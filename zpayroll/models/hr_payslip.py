from dateutil.relativedelta import relativedelta
from odoo import api, models, fields, _
from odoo.exceptions import UserError
import base64
from datetime import datetime, time

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
    payslip_nickname = fields.Char(string='Nombre personalizado de boleta',
                                   compute='_compute_payslip_nickname',store=True)
    
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
                slip.payroll_year = False
                slip.payroll_period_code = False
     
    ### cambia el nombre de la nomina            
    @api.depends('employee_id','payroll_type','payroll_month','payroll_year',)
    def _compute_payslip_nickname(self):
        for slip in self:
            if not slip.employee_id or not slip.payroll_month or not slip.payroll_year:
                slip.payslip_nickname = False
                continue

            month_labels = dict(slip._fields['payroll_month'].selection)
            payroll_type_labels = dict(slip._fields['payroll_type'].selection)

            month_name = month_labels.get(slip.payroll_month, slip.payroll_month)
            payroll_type_name = payroll_type_labels.get(
                slip.payroll_type or 'nomina',
                slip.payroll_type or 'nomina')

            slip.payslip_nickname = '%s de %s - %s %s' % (
                payroll_type_name,
                slip.employee_id.name,
                month_name,
                slip.payroll_year)
    
    # limpiar empleado y contrato al cambiar compañía
    @api.onchange('company_id')
    def _onchange_company_id(self):
        for slip in self:
            slip.employee_id = False
            slip.contract_id = False
            slip.struct_id = False

            domain = []
            if slip.company_id:
                domain = ['|',
                          ('company_id', '=', False),
                          ('company_id', '=', slip.company_id.id)]

            return {
                'domain': {
                    'employee_id': domain,
                    'contract_id': [('company_id', '=', slip.company_id.id)] if slip.company_id else []
                }
            }
            
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
    r5_renta_bruta_anual = fields.Float(
    string='Renta Bruta Anual 5ta',
    compute='_compute_renta_5ta_retencion',
    store=True
    )

    r5_impuesto_anual = fields.Float(
        string='Impuesto Anual 5ta',
        compute='_compute_renta_5ta_retencion',
        store=True
    )

    r5_retenciones_anteriores = fields.Float(
        string='Retenciones 5ta Anteriores',
        compute='_compute_renta_5ta_retencion',
        store=True
    )

    renta_5ta_retencion = fields.Float(
        string='Retención 5ta',
        compute='_compute_renta_5ta_retencion',
        store=True
    )
    
    ##############################################
    ##############################################
    ### Metodos para el Calculo de Renta de 5ta
    @api.depends(
        'employee_id',
        'contract_id',
        'date_from',
        'date_to',
        'line_ids.total',
        'line_ids.salary_rule_id',
        'line_ids.salary_rule_id.is_taxable_r5',
        'line_ids.salary_rule_id.is_r5_projection_base',
    )
    def _compute_renta_5ta_retencion(self):
        for slip in self:
            slip.r5_renta_bruta_anual = 0.0
            slip.r5_impuesto_anual = 0.0
            slip.r5_retenciones_anteriores = 0.0
            slip.renta_5ta_retencion = 0.0

            if not slip.employee_id or not slip.contract_id or not slip.payroll_month_number:
                continue

            month = slip.payroll_month_number

            previous_withholding = slip._get_previous_r5_withholding_amount(
                r5_rule_code='R5_RET'
            )

            # DICIEMBRE: se usa renta real anual
            if month == 12:
                renta_bruta_anual = slip._calculate_real_r5_annual_income()
                impuesto_anual = slip._calculate_r5_annual_tax(renta_bruta_anual)

                retencion_mes = impuesto_anual - previous_withholding
                retencion_mes = max(retencion_mes, 0.0)

            # ENERO A NOVIEMBRE: se usa renta proyectada
            else:
                renta_bruta_anual = slip._calculate_r5_projected_gross_annual_income()
                impuesto_anual = slip._calculate_r5_annual_tax(renta_bruta_anual)

                saldo_impuesto = impuesto_anual - previous_withholding

                if saldo_impuesto <= 0:
                    retencion_mes = 0.0
                else:
                    divisor = 13 - month
                    retencion_mes = saldo_impuesto / divisor

                retencion_mes = max(retencion_mes, 0.0)

            slip.r5_renta_bruta_anual = round(renta_bruta_anual, 2)
            slip.r5_impuesto_anual = round(impuesto_anual, 2)
            slip.r5_retenciones_anteriores = round(previous_withholding, 2)
            slip.renta_5ta_retencion = round(retencion_mes, 2)
    
    
    def _calculate_real_r5_annual_income(self):
        """
        Calcula la renta bruta anual real afecta a renta de quinta.

        Suma:
        1. Las boletas anteriores del mismo año con reglas afectas a quinta.
        2. La boleta actual, leyendo self.line_ids.

        Esta versión sirve para la prueba de doble cálculo en diciembre.
        """

        self.ensure_one()

        if not self.employee_id or not self.payroll_year or not self.payroll_month_number:
            return 0.0

        previous_payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('payroll_year', '=', self.payroll_year),
            ('payroll_month_number', '<', self.payroll_month_number),
            ('payroll_type', '=', 'nomina'),
            ('id', '!=', self.id),
        ])

        amount = 0.0

        # 1. Boletas anteriores del año
        for slip in previous_payslips:
            for line in slip.line_ids:
                rule = line.salary_rule_id

                if not rule:
                    continue

                if rule.is_taxable_r5:
                    amount += line.total or 0.0

        # 2. Boleta actual
        for line in self.line_ids:
            rule = line.salary_rule_id

            if not rule:
                continue

            if rule.is_taxable_r5:
                amount += line.total or 0.0

        return round(amount, 2)


    def _get_r5_projection_rules_amount(self):
        """
        Suma los conceptos usados en proyectado 5ta de boletas anteriores
        del mismo año de planilla, más la boleta actual.

        Se usa payroll_year y payroll_month_number para evitar errores
        con periodos que empiezan en el mes anterior, por ejemplo:
        25/12/2025 - 24/01/2026.
        """

        self.ensure_one()

        if not self.employee_id or not self.payroll_year or not self.payroll_month_number:
            return 0.0

        previous_payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('payroll_year', '=', self.payroll_year),
            ('payroll_month_number', '<', self.payroll_month_number),
            ('payroll_type', '=', 'nomina'),
            ('state', '!=', 'cancel'),
            ('id', '!=', self.id),
        ])

        amount = 0.0

        # 1. Boletas anteriores del año de planilla
        for slip in previous_payslips:
            for line in slip.line_ids:
                rule = line.salary_rule_id

                if not rule:
                    continue

                if rule.is_r5_projection_base:
                    amount += line.total or 0.0

        # 2. Boleta actual
        for line in self.line_ids:
            rule = line.salary_rule_id

            if not rule:
                continue

            if rule.is_r5_projection_base:
                amount += line.total or 0.0

        return round(amount, 2)


    def _calculate_r5_projected_gross_annual_income(self):
        """
        Calcula la renta bruta anual proyectada de quinta categoria.

        Formula:
            wage x 14
        + wage x 0.09 x 2
        + reglas salariales marcadas como is_r5_projection_base
            en las boletas del año
        """

        self.ensure_one()

        contract = self.contract_id

        if not contract:
            return 0.0

        wage = contract.wage or 0.0

        if wage <= 0:
            return 0.0

        extraordinary_bonus_rate = 0.09

        annual_wage = wage * 14
        annual_extraordinary_bonus = wage * extraordinary_bonus_rate * 2
        r5_projection_rules_amount = self._get_r5_projection_rules_amount()

        renta_bruta_anual = (
            annual_wage
            + annual_extraordinary_bonus
            + r5_projection_rules_amount
        )

        return round(renta_bruta_anual, 2)


    def _calculate_r5_annual_tax(self, renta_bruta_anual):
        """
        Calcula el impuesto anual de quinta categoria
        a partir de la renta_bruta_anual.

        Primero deduce 7 UIT y luego aplica los tramos progresivos.
        """

        self.ensure_one()

        uit = self.uit or 0.0
        renta_bruta_anual = renta_bruta_anual or 0.0

        if not uit or renta_bruta_anual <= 0:
            return 0.0

        # SUNAT: Renta Bruta Anual - 7 UIT
        renta_neta_imponible = renta_bruta_anual - (7 * uit)

        if renta_neta_imponible <= 0:
            return 0.0

        tax = 0.0
        remaining = renta_neta_imponible

        brackets = [
            (5 * uit, 0.08),
            (15 * uit, 0.14),
            (15 * uit, 0.17),
            (10 * uit, 0.20),
            (float('inf'), 0.30),
        ]

        for bracket_amount, rate in brackets:
            if remaining <= 0:
                break

            taxable_part = min(remaining, bracket_amount)
            tax += taxable_part * rate
            remaining -= taxable_part

        return round(tax, 2)


    def _get_previous_r5_withholding_amount(self, r5_rule_code='R5_RET'):
        """
        Suma las retenciones anteriores de quinta categoria del mismo año.

        Usa:
        - payroll_year
        - payroll_month_number

        No depende de date_from ni date_to.
        """

        self.ensure_one()

        if not self.employee_id or not self.payroll_year or not self.payroll_month_number:
            return 0.0

        previous_payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('payroll_year', '=', self.payroll_year),
            ('payroll_month_number', '<', self.payroll_month_number),
            ('payroll_type', '=', 'nomina'),
            ('id', '!=', self.id),
        ])

        amount = 0.0

        for slip in previous_payslips:
            for line in slip.line_ids:
                if line.code == r5_rule_code:
                    amount += abs(line.total or 0.0)

        return round(amount, 2)
        


    def _calculate_r5_monthly_withholding(self, r5_rule_code='R5_RET'):
        """
        Calcula la retención mensual de renta de quinta.

        Enero a noviembre:
            renta proyectada anual
            - retenciones anteriores
            / divisor

        Diciembre:
            renta real anual
            - retenciones anteriores
            = regularización
        """

        self.ensure_one()

        if not self.payroll_month_number:
            return 0.0

        month = self.payroll_month_number

        previous_withholding = self._get_previous_r5_withholding_amount(
            r5_rule_code=r5_rule_code
        )

        # DICIEMBRE: se usa renta real anual
        if month == 12:
            renta_bruta_anual = self._calculate_real_r5_annual_income()
            impuesto_anual = self._calculate_r5_annual_tax(renta_bruta_anual)

            retencion_mes = impuesto_anual - previous_withholding
            retencion_mes = max(retencion_mes, 0.0)

            return round(retencion_mes, 2)

        # ENERO A NOVIEMBRE: se usa renta proyectada anual
        renta_bruta_anual = self._calculate_r5_projected_gross_annual_income()
        impuesto_anual = self._calculate_r5_annual_tax(renta_bruta_anual)

        saldo_impuesto = impuesto_anual - previous_withholding

        if saldo_impuesto <= 0:
            return 0.0

        divisor = 13 - month
        retencion_mes = saldo_impuesto / divisor

        return round(max(retencion_mes, 0.0), 2)
    
    
    def calculate_r5_retention_for_salary_rule(self):
        """
        Metodo publico para ser llamado desde la regla salarial R5_RET.

        La regla salarial no debe pasar parametros ni armar la logica.
        Solo llama este metodo y recibe la retencion mensual.
        """

        self.ensure_one()

        return self._calculate_r5_monthly_withholding(r5_rule_code='R5_RET')
    
    #########################
    #calculo de dicembre renta d e5ta
    r5_debug_real_income_dec = fields.Float(
    string='DEBUG 5ta - Renta Real Dic',
    compute='_compute_r5_december_debug',
    store=False
    )

    r5_debug_tax_dec = fields.Float(
        string='DEBUG 5ta - Impuesto Anual Dic',
        compute='_compute_r5_december_debug',
        store=False
    )

    r5_debug_previous_withholding_dec = fields.Float(
        string='DEBUG 5ta - Retenciones Anteriores Dic',
        compute='_compute_r5_december_debug',
        store=False
    )

    r5_debug_retention_dec = fields.Float(
        string='DEBUG 5ta - Retención Dic',
        compute='_compute_r5_december_debug',
        store=True
    )

    r5_debug_error_dec = fields.Text(
        string='DEBUG 5ta - Error Dic',
        compute='_compute_r5_december_debug',
        store=False
    )        
    
    @api.depends(
    'employee_id',
    'contract_id',
    'payroll_year',
    'payroll_month_number',
    'payroll_type',
    'line_ids.total',
    'line_ids.code',
    'line_ids.salary_rule_id',
    'line_ids.salary_rule_id.is_taxable_r5',
    )
    def _compute_r5_december_debug(self):
        for slip in self:
            slip.r5_debug_real_income_dec = 0.0
            slip.r5_debug_tax_dec = 0.0
            slip.r5_debug_previous_withholding_dec = 0.0
            slip.r5_debug_retention_dec = 0.0
            slip.r5_debug_error_dec = False

            try:
                if not slip.employee_id:
                    slip.r5_debug_error_dec = 'No hay empleado.'
                    continue

                if not slip.payroll_year:
                    slip.r5_debug_error_dec = 'No hay payroll_year.'
                    continue

                if not slip.payroll_month_number:
                    slip.r5_debug_error_dec = 'No hay payroll_month_number.'
                    continue

                if slip.payroll_type != 'nomina':
                    slip.r5_debug_error_dec = 'La boleta no es de tipo nomina.'
                    continue

                if slip.payroll_month_number != 12:
                    slip.r5_debug_error_dec = 'No es diciembre. Debug aplica solo para mes 12.'
                    continue

                renta_bruta_anual = slip._calculate_real_r5_annual_income()

                impuesto_anual = slip._calculate_r5_annual_tax(
                    renta_bruta_anual
                )

                previous_withholding = slip._get_previous_r5_withholding_amount(
                    r5_rule_code='R5_RET'
                )

                retencion_diciembre = impuesto_anual - previous_withholding
                retencion_diciembre = max(retencion_diciembre, 0.0)

                slip.r5_debug_real_income_dec = round(renta_bruta_anual, 2)
                slip.r5_debug_tax_dec = round(impuesto_anual, 2)
                slip.r5_debug_previous_withholding_dec = round(previous_withholding, 2)
                slip.r5_debug_retention_dec = round(retencion_diciembre, 2)

            except Exception as e:
                slip.r5_debug_error_dec = str(e)
                
                
    def calculate_r5_december_retention_from_current_base(self, current_r5_base):
        self.ensure_one()

        previous_real_income = self._get_previous_real_r5_taxable_amount()

        renta_bruta_anual = previous_real_income + (current_r5_base or 0.0)

        impuesto_anual = self._calculate_r5_annual_tax(renta_bruta_anual)

        previous_withholding = self._get_previous_r5_withholding_amount('R5_RET')

        retencion_mes = impuesto_anual - previous_withholding

        return round(max(retencion_mes, 0.0), 2)        
                
                
    def _get_previous_real_r5_taxable_amount(self):
        """
        Suma la renta real afecta a quinta de boletas anteriores del mismo año.
        No incluye la boleta actual.
        """

        self.ensure_one()

        if not self.employee_id or not self.payroll_year or not self.payroll_month_number:
            return 0.0

        previous_payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('payroll_year', '=', self.payroll_year),
            ('payroll_month_number', '<', self.payroll_month_number),
            ('payroll_type', 'in', ['nomina', 'gratificacion']),
            ('id', '!=', self.id),
            ('state', '!=', 'cancel'),
        ])

        amount = 0.0

        for slip in previous_payslips:
            for line in slip.line_ids:
                rule = line.salary_rule_id

                if not rule:
                    continue

                if rule.is_taxable_r5:
                    amount += line.total or 0.0

        return round(amount, 2)         
                
    ##############################################################################
    ##############################
    #envio de correos
    def action_send_boleta_pago_email_employee(self):
        # Seguridad: solo usuarios autorizados pueden enviar boletas
        if not self.env.user.has_group("hr_payroll_community.group_hr_payroll_community_user"):
            raise UserError(_("No tienes permisos para enviar boletas de pago."))

        # Correo en copia
        email_cc = "jbernui@gerens.pe"  # Cambia aquí el correo en copia

        email_from = (
            self.env.user.partner_id.email_formatted
            or self.env.company.partner_id.email_formatted
        )

        if not email_from:
            raise UserError(
                _("Configura un correo en el usuario actual o en la compañía.")
            )

        report_action = self.env.ref(
            "zpayroll.action_report_boleta_pago",
            raise_if_not_found=False,
        )

        if not report_action:
            raise UserError(
                _("No se encontró el reporte zpayroll.action_report_boleta_pago.")
            )

        sent_count = 0
        skipped_employees = []

        for slip in self:
            employee = slip.employee_id
            employee_name = employee.name or "Empleado"

            # Correo del empleado
            email_to = employee.work_email

            if not email_to:
                skipped_employees.append(employee_name)
                continue

            pdf_content, content_type = report_action.sudo()._render_qweb_pdf(
                report_action.report_name,
                res_ids=slip.ids,
            )

            boleta_name = slip.payslip_nickname or slip.name or employee_name
            filename = "%s.pdf" % boleta_name

            attachment = self.env["ir.attachment"].sudo().create({
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(pdf_content),
                "res_model": slip._name,
                "res_id": slip.id,
                "mimetype": "application/pdf",
            })

            subject = "Boleta de Pago - %s" % boleta_name

            body_html = """
                <p>Estimado(a) %s,</p>
                <p>Adjunto encontrará su boleta de pago correspondiente.</p>
                <p>Saludos.</p>
            """ % employee_name

            mail = self.env["mail.mail"].sudo().create({
                "subject": subject,
                "email_from": email_from,
                "email_to": email_to,
                "email_cc": email_cc,
                "body_html": body_html,
                "attachment_ids": [(6, 0, [attachment.id])],
                "auto_delete": False,
            })

            mail.send(raise_exception=False)
            sent_count += 1

        message = _("Se envió %s boleta(s).") % sent_count

        if skipped_employees:
            message += _(" No se enviaron boletas a empleados sin correo: %s") % (
                ", ".join(skipped_employees)
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Envío de boletas"),
                "message": message,
                "type": "success" if sent_count else "warning",
                "sticky": True if skipped_employees else False,
            },
        }