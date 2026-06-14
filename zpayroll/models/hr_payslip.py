from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    uit = fields.Float(string='UIT',default=5500.0)
    rmv = fields.Float(string='RMV', default=1130.0)
    onp_rate = fields.Float(string='% ONP', default=13.0)
    essalud_rate = fields.Float(string='% EsSalud', default=9.0)
    eps = fields.Float(string='% EPS', default=2.25)
    eps_essalud_rate = fields.Float(string='% EPS EsSalud', default=6.75)
    
    payroll_type = fields.Selection([('nomina', 'Nómina mensual'),
                                ('cts', 'CTS'),
                                ('gratificacion', 'Gratificación'),
                                ('liquidacion', 'Liquidación'),], string='Tipo de nómina', default='nomina')
    
    payroll_month = fields.Selection([('01', 'ENERO'),
                            ('02', 'FEBRERO'),
                            ('03', 'MARZO'),
                            ('04', 'ABRIL'),
                            ('05', 'MAYO'),
                            ('06', 'JUNIO'),
                            ('07', 'JULIO'),
                            ('08', 'AGOSTO'),
                            ('09', 'SEPTIEMBRE'),
                            ('10', 'OCTUBRE'),
                            ('11', 'NOVIEMBRE'),
                            ('12', 'DICIEMBRE'), ], string='Mes', compute='_compute_payroll_period', store=True)
    

    payroll_year = fields.Char(string='Año',compute='_compute_payroll_period',store=True)
    payroll_month_number = fields.Integer(string='Nro. Mes',compute='_compute_payroll_period',store=True)
    payroll_period_code = fields.Char(string='Periodo',compute='_compute_payroll_period',store=True)
    
    #metodo para el calculo de los campos que identifican a al nomina    
    @api.depends('date_to')
    def _compute_payroll_period(self):
        for slip in self:
            if slip.date_to:
                slip.payroll_month = str(slip.date_to.month).zfill(2)
                slip.payroll_month_number = slip.date_to.month
                slip.payroll_year = str(slip.date_to.year)
                slip.payroll_period_code = f"{slip.date_to.year}-{str(slip.date_to.month).zfill(2)}"
            else:
                slip.payroll_month = False
                slip.payroll_month_number = 0
                slip.payroll_year = 0
                slip.payroll_period_code = False
                
    
    #########################################
        #CAlculo de Remuneracion_computable
    remuneracion_computable = fields.Float(string='Remuneración Computable Base',
                            compute='_compute_remuneracion_computable',store=True)
    
    #Metodo de busqueda en las relsa salariales
    def _get_variable_computable_amount(self, slip):
        lines = slip.line_ids.filtered(
            lambda l: l.salary_rule_id.is_computable and l.salary_rule_id.is_variable
        )
        return sum(lines.mapped('total'))
    
    #suma todos los montos en los conceptos
    def _get_fixed_computable_amount(self, slip):
        lines = slip.line_ids.filtered(
            lambda l: l.salary_rule_id.is_computable
            and not l.salary_rule_id.is_variable
        )
        return sum(lines.mapped('total'))

    #claculo principal y la logica si son regulares mayor/igual a 3 meses
    @api.depends('employee_id','date_to','line_ids.total',
                'line_ids.salary_rule_id.is_computable','line_ids.salary_rule_id.is_variable')
    def _compute_remuneracion_computable(self):
        for slip in self:
            slip.remuneracion_computable = 0.0

            if not slip.employee_id or not slip.date_to:
                continue

            # 1. Parte fija computable del mes actual
            fixed_computable = slip._get_fixed_computable_amount(slip)

            # 2. Buscar 6 nóminas mensuales anteriores
            previous_slips = self.search([
                ('employee_id', '=', slip.employee_id.id),
                ('date_to', '<', slip.date_to),
                ('state', 'in', ['done', 'paid']),
                ('payroll_type', '=', 'nomina'),
                ('id', '!=', slip.id),
            ], order='date_to desc', limit=6)

            # 3. Promedio 1/6 de variables computables
            total_variable = 0.0
            count_months = 0

            for previous_slip in previous_slips:
                amount = slip._get_variable_computable_amount(previous_slip)

                if amount > 0:
                    total_variable += amount
                    count_months += 1

            variable_computable = total_variable / 6.0 if count_months >= 3 else 0.0

            # 4. Resultado final
            slip.remuneracion_computable = fixed_computable + variable_computable
            
    
    ##############TEST
    renta_5ta_retencion = fields.Float( string='Retención 5ta',compute='_compute_renta_5ta_retencion', store=True)
    
    ##############################################
    ### Metodos para el CAlculo de Renta de 5ta
    def _get_r5_taxable_amount(self, slip, exclude_projection_base=False):
        lines = slip.line_ids.filtered(
            lambda l: l.salary_rule_id.is_taxable_r5
        )

        if exclude_projection_base:
            lines = lines.filtered(
                lambda l: not l.salary_rule_id.is_r5_projection_base
            )

        return sum(lines.mapped('total'))


    def _get_previous_r5_extra_income(self):
        self.ensure_one()

        previous_slips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('payroll_year', '=', self.payroll_year),
            ('payroll_month_number', '<', self.payroll_month_number),
            ('payroll_type', '=', 'nomina'),
            ('state', 'in', ['done', 'paid']),
        ])

        total = 0.0

        for slip in previous_slips:
            total += self._get_r5_taxable_amount(
                slip,
                exclude_projection_base=True
            )

        return total

    ##Obtiene la retencion previa en anteriores boleta de nomina
    def _get_previous_r5_withholding(self):
        self.ensure_one()

        previous_slips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('payroll_year', '=', self.payroll_year),
            ('payroll_month_number', '<', self.payroll_month_number),
            ('payroll_type', '=', 'nomina'),
            ('state', 'in', ['done', 'paid']),
        ])

        total = 0.0

        for slip in previous_slips:
            lines = slip.line_ids.filtered(lambda l: l.code == 'R5_RET')
            total += abs(sum(lines.mapped('total')))

        return total

    #Calculo del porctentaje de acuedo al monto que esta afecto a retencion
    def _calculate_r5_annual_tax(self, annual_income):
        self.ensure_one()

        uit = self.uit or 0.0
        deduction = 7 * uit

        net_income = annual_income - deduction

        if net_income <= 0:
            return 0.0

        tax = 0.0
        remaining = net_income

        #Tramos dodne cae la renta neta imponilbe
        brackets = [
            (5 * uit, 0.08),
            (20 * uit, 0.14),
            (35 * uit, 0.17),
            (45 * uit, 0.20),
            (float('inf'), 0.30),
        ]

        for limit, rate in brackets:
            taxable_part = min(remaining, limit)

            if taxable_part <= 0:
                break

            tax += taxable_part * rate
            remaining -= taxable_part

        return tax

    @api.depends('line_ids.total','contract_id.wage','payroll_month_number','payroll_year','employee_id')
    def _compute_renta_5ta_retencion(self):
        for slip in self:

            if not slip.employee_id or not slip.payroll_year or not slip.payroll_month_number:
                slip.renta_5ta_retencion = 0.0
                continue

            previous_withholding = slip._get_previous_r5_withholding()

            # DICIEMBRE
            if slip.payroll_month_number == 12:

                slips_year = slip.env['hr.payslip'].search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('payroll_year', '=', slip.payroll_year),
                    ('payroll_type', '=', 'nomina'),
                    ('state', 'in', ['done', 'paid']),
                ])

                annual_real_income = 0.0

                for s in slips_year:
                    annual_real_income += slip._get_r5_taxable_amount(s)

                annual_tax = slip._calculate_r5_annual_tax(annual_real_income)

                result = annual_tax - previous_withholding

                slip.renta_5ta_retencion = result if result > 0 else 0.0

            else:
                monthly_salary = slip.contract_id.wage or 0.0

                projected_base_income = monthly_salary * 14

                extra_income = slip._get_previous_r5_extra_income()

                projected_annual_income = projected_base_income + extra_income

                annual_tax = slip._calculate_r5_annual_tax(projected_annual_income)

                previous_withholding = slip._get_previous_r5_withholding()

                pending_tax = annual_tax - previous_withholding

                if pending_tax <= 0:
                    slip.renta_5ta_retencion = 0.0
                    continue

                months_to_divide = 12 - slip.payroll_month_number + 1

                slip.renta_5ta_retencion = pending_tax / months_to_divide