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
            
    ###################################
    ############## RENTA DE QUINTA
    ## Suma retenciones de renta d equinta que estan en anominas anteriores
    def get_previous_amount(self, code,search_by='rule',payroll_types=None,use_absolute=True,
                                    same_company=True,include_child_categories=True,):
        """Suma montos de boletas anteriores.
        search_by:
            'rule'     -> busca por código de regla salarial, ejemplo: R5_RET
            'category' -> busca por código de categoría, ejemplo: PE_REM_COMP
        """

        self.ensure_one()

        if not self.employee_id or not self.payroll_year or not self.payroll_month_number:
            return 0.0

        if payroll_types is None:
            payroll_types = ['nomina']

        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('payroll_year', '=', self.payroll_year),
            ('payroll_month_number', '<', self.payroll_month_number),
            ('id', '!=', self.id),
            ('state', '!=', 'cancel'),
            ('payroll_type', 'in', payroll_types),]

        if same_company and self.company_id:
            domain.append(('company_id', '=', self.company_id.id))

        previous_payslips = self.env['hr.payslip'].search(domain)

        category_ids = []

        if search_by == 'category':
            category = self.env['hr.salary.rule.category'].search([
                ('code', '=', code)
            ], limit=1)

            if not category:
                return 0.0

            if include_child_categories:
                categories = self.env['hr.salary.rule.category'].search([
                    ('id', 'child_of', category.id)
                ])
                category_ids = categories.ids
            else:
                category_ids = [category.id]

        amount = 0.0

        for slip in previous_payslips:
            for line in slip.line_ids:
                line_amount = line.total or 0.0

                if search_by == 'rule':
                    if line.code == code:
                        amount += abs(line_amount) if use_absolute else line_amount

                elif search_by == 'category':
                    rule = line.salary_rule_id

                    if not rule or not rule.category_id:
                        continue

                    if rule.category_id.id in category_ids:
                        amount += abs(line_amount) if use_absolute else line_amount

        return round(amount, 2)
    
    
    ######### Proyeccion r5ta (con salario, y salario d eotro empleo, teneidno en ceunta asgnacion familair)
    def calculate_r5_projected(self, wage=0.0, other_wage=0.0):
        self.ensure_one()

        renta_actual = self.calculate_r5_projected_wage(
            wage,
            include_family_allowance=True)

        renta_otro_trabajo = self.calculate_r5_projected_wage(
            other_wage,
            include_family_allowance=True)

        return round(renta_actual + renta_otro_trabajo, 2)
    
    ###################  CAlculo simple de un sueldo apr aproyeccion
    def calculate_r5_projected_wage(self, wage=0.0, include_family_allowance=True):
        """
        Proyecta un sueldo mensual para renta de quinta:
        (wage + asignación familiar) x factor anual
        """

        self.ensure_one()

        try:
            wage = float(wage or 0.0)
        except Exception:
            wage = 0.0

        if wage <= 0:
            return 0.0

        asignacion_familiar = 0.0

        if include_family_allowance:
            if self.employee_id and self.employee_id.has_family_allowance():
                asignacion_familiar = (self.rmv or 0.0) * 0.10

        factor_anual = 14 + (2 * ((self.essalud_rate or 0.0) / 100))

        return round((wage + asignacion_familiar) * factor_anual, 2)

    ##### Calculo de impuesto anualde renta de quinta
    def calculate_r5_annual_tax(self, renta_bruta_anual=0.0):
        self.ensure_one()

        try:renta_bruta_anual = float(renta_bruta_anual or 0.0)
        except Exception:renta_bruta_anual = 0.0

        uit = self.uit or 0.0
        if not uit or renta_bruta_anual <= 0:
            return 0.0

        # Deducción legal: 7 UIT
        renta_neta_imponible = renta_bruta_anual - (7 * uit)
        if renta_neta_imponible <= 0:
            return 0.0

        impuesto = 0.0
        restante = renta_neta_imponible
        tramos = [
            (5 * uit, 0.08),
            (15 * uit, 0.14),
            (15 * uit, 0.17),
            (10 * uit, 0.20),
            (None, 0.30),]

        for limite_tramo, tasa in tramos:
            if restante <= 0:
                break

            if limite_tramo is None:
                parte_afecta = restante
            else:
                parte_afecta = min(restante, limite_tramo)

            impuesto += parte_afecta * tasa
            restante -= parte_afecta

        return round(impuesto, 2)
    
    ### metodo para le calculo de rtencion mensual
    def calculate_r5_monthly_retention_simple(self, projected_annual_tax=0.0):       
        self.ensure_one()

        try: projected_annual_tax = float(projected_annual_tax or 0.0)
        except Exception: projected_annual_tax = 0.0

        month = self.payroll_month_number or 0

        try: month = int(month)
        except Exception:month = 0

        if month <= 0:
            return 0.0
        # Diciembre lo manejaremos aparte en la regla salarial
        if month == 12:
            return 0.0
        divisor = 13 - month
        if divisor <= 0:
            return 0.0

        retencion = projected_annual_tax / divisor

        return round(max(retencion, 0.0), 2)
        
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
        
    
    
   