from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    payroll_type = fields.Selection([('cts', 'CTS'),], string='Tipo de nómina',copy=False,)
    payroll_year = fields.Integer(string='Año',copy=False,)
    cts_month = fields.Selection([('5', 'MAYO'),('11', 'NOVIEMBRE'),],string='Mes CTS',copy=False,)
    struct_id = fields.Many2one('hr.payroll.structure',string='Estructura salarial',ondelete='restrict',copy=False,)
    company_id = fields.Many2one('res.company',string='Empresa', default=lambda self: self.env.company,copy=False,)

    computable_date_from = fields.Date(string='Inicio período computable CTS',copy=False,)
    computable_date_to = fields.Date(string='Fin período computable CTS',copy=False,)
    
    
        
    ##########
    def action_generate_cts(self):
        self.ensure_one()

        # ---------------------------------------------------------
        # 1. Validaciones del lote
        # ---------------------------------------------------------

        if self.state != 'draft':
            raise UserError(
                _("El lote debe estar en estado borrador.")
            )

        if self.payroll_type != 'cts':
            raise UserError(
                _("Este proceso solo puede ejecutarse para un lote CTS.")
            )

        if not self.payroll_year:
            raise UserError(
                _("Debe indicar el año.")
            )

        if not self.cts_month:
            raise UserError(
                _("Debe indicar el mes CTS: mayo o noviembre.")
            )

        if not self.struct_id:
            raise UserError(
                _("Debe seleccionar la estructura salarial CTS.")
            )

        if not self.company_id:
            raise UserError(
                _("Debe indicar la empresa.")
            )

        year = int(self.payroll_year)
        month = int(self.cts_month)

        if month not in (5, 11):
            raise UserError(
                _("El mes CTS solo puede ser mayo o noviembre.")
            )

        month_name = 'MAYO' if month == 5 else 'NOVIEMBRE'

        Payslip = self.env['hr.payslip']
        Contract = self.env['hr.contract']

        # ---------------------------------------------------------
        # 2. Buscar contratos activos de la empresa
        # ---------------------------------------------------------

        contracts = Contract.search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'open'),
            ('date_start', '<=', self.date_end),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', self.date_start),
        ])

        if not contracts:
            raise UserError(
                _("No se encontraron contratos activos para este período.")
            )

        created_ids = []
        skipped_ids = []

        # ---------------------------------------------------------
        # 3. Crear una CTS por trabajador
        # ---------------------------------------------------------

        for contract in contracts:

            employee = contract.employee_id

            if not employee:
                continue

            # -----------------------------------------------------
            # Evitar duplicados
            # -----------------------------------------------------

            existing = Payslip.search([
                ('employee_id', '=', employee.id),
                ('payroll_type', '=', 'cts'),
                ('payroll_year', '=', str(year)),
                ('payroll_month_number', '=', month),
                ('state', '!=', 'cancel'),
            ], limit=1)

            if existing:
                skipped_ids.append(employee.id)
                continue

            payslip_name = (
                "CTS de %s - %s %s"
                % (
                    employee.name,
                    month_name,
                    year,
                )
            )

            # -----------------------------------------------------
            # Crear cascarón hr.payslip
            # -----------------------------------------------------

            payslip = Payslip.create({
                'employee_id': employee.id,
                'contract_id': contract.id,
                'company_id': self.company_id.id,

                'date_from': self.date_start,
                'date_to': self.date_end,

                'state': 'draft',

                'name': payslip_name,

                'struct_id': self.struct_id.id,

                'payslip_run_id': self.id,

                'payroll_type': 'cts',

                'payroll_year': str(year),

                'payroll_month_number': month,
            })

            # -----------------------------------------------------
            # Ejecutar motor de reglas salariales
            # -----------------------------------------------------

            payslip.action_compute_sheet()

            created_ids.append(payslip.id)

        # ---------------------------------------------------------
        # 4. Resultado
        # ---------------------------------------------------------

        if not created_ids:
            raise UserError(
                _(
                    "No se generó ninguna CTS. "
                    "Es posible que todos los empleados ya tengan "
                    "una CTS para %s %s."
                ) % (month_name, year)
            )

        # Abrir las boletas CTS recién generadas
        return {
            'type': 'ir.actions.act_window',
            'name': 'CTS %s %s' % (month_name, year),
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_ids)],
            'context': {
                'create': False,
            },
        }