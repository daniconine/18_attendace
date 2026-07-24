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
    
    
    _sql_constraints = [('unique_payslip_employee_type_period',
                    'unique(employee_id, payroll_type, payroll_year, payroll_month_number)',
                    'Ya existe una nómina de este tipo para este empleado en el mismo mes y año.')]
                
    #####################################################################
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
    ajuste_remuneracion_computable = fields.Float(string='Ajuste Rem. Computable',default=0.0,
                    help='Monto manual para ajustar la Remuneración Computable Base (ej. en migraciones o correcciones de variables).')
    
    #CAlculo de Remuneracion_computable RC_B
    remuneracion_computable = fields.Float(string='Remuneración Computable Base',
                            compute='_compute_remuneracion_computable',store=True)
    
  
    def _get_family_allowance_amount(self):
        self.ensure_one()

        if self.employee_id and self.employee_id.has_family_allowance():
            return (self.rmv or 0.0) * 0.10

        return 0.0


    def _get_fixed_computable_base_from_contract(self):
        self.ensure_one()

        contract = self.contract_id
        if not contract:
            return 0.0

        wage = contract.wage or 0.0
        asignacion_familiar = self._get_family_allowance_amount()
        bono_fijo = contract.bono_fijo_computable_mensual or 0.0
        concepto_fijo = contract.concepto_fijo_computable_mensual or 0.0

        return wage + asignacion_familiar + bono_fijo + concepto_fijo


    def _get_previous_month_periods(self, reference_date, months=6):
        periods = []

        if not reference_date:
            return periods

        base_date = reference_date.replace(day=1)

        for i in range(1, months + 1):
            period_date = base_date - relativedelta(months=i)

            periods.append({
                'year': str(period_date.year),
                'month_number': period_date.month,
                'period_code': f'{period_date.year}-{period_date.month:02d}',
            })

        return periods


    def _get_previous_nomina_slips_by_month(self, slip, months=6):
        Payslip = self.env['hr.payslip']
        previous_slips = Payslip.browse()

        if not slip.employee_id or not slip.date_to:
            return previous_slips

        periods = self._get_previous_month_periods(slip.date_to, months=months)

        for period in periods:
            monthly_slip = Payslip.search([
                ('employee_id', '=', slip.employee_id.id),
                ('payroll_type', '=', 'nomina'),
                ('payroll_year', '=', period['year']),
                ('payroll_month_number', '=', period['month_number']),
                ('id', '!=', slip.id),
                ('state', '!=', 'cancel'),
            ], order='date_to desc, write_date desc, id desc', limit=1)

            if monthly_slip:
                previous_slips |= monthly_slip

        return previous_slips


    def _get_regular_variable_computable_amount(self, previous_slips):
        variable_data = {}

        for previous_slip in previous_slips:
            lines = previous_slip.line_ids.filtered(
                lambda l: l.salary_rule_id.is_computable
                and l.salary_rule_id.is_variable
                and l.total > 0
            )

            monthly_rules = {}

            for line in lines:
                rule = line.salary_rule_id
                key = rule.code or str(rule.id)

                if key not in monthly_rules:
                    monthly_rules[key] = {
                        'name': rule.name,
                        'amount': 0.0,
                    }

                monthly_rules[key]['amount'] += line.total

            for key, data in monthly_rules.items():
                if key not in variable_data:
                    variable_data[key] = {
                        'name': data['name'],
                        'total': 0.0,
                        'months': 0,
                    }

                variable_data[key]['total'] += data['amount']
                variable_data[key]['months'] += 1

        total_regular_variable = 0.0

        for key, data in variable_data.items():
            if data['months'] >= 3:
                total_regular_variable += data['total']

        return total_regular_variable / 6.0


    @api.depends('employee_id','date_to','contract_id','contract_id.wage','contract_id.bono_fijo_computable_mensual',
                'contract_id.concepto_fijo_computable_mensual','rmv','line_ids.total','line_ids.salary_rule_id.is_computable',
                'line_ids.salary_rule_id.is_variable')
    def _compute_remuneracion_computable(self):
        for slip in self:
            slip.remuneracion_computable = 0.0

            if not slip.employee_id or not slip.date_to:
                continue

            # 1. Parte fija computable desde contrato vigente de la boleta
            fixed_computable = slip._get_fixed_computable_base_from_contract()
            
            # 2. Buscar una nómina mensual por cada uno de los 6 meses anteriores
            previous_slips = slip._get_previous_nomina_slips_by_month(slip,months=6)

            # 3. Promedio de variables computables regulares por concepto
            variable_computable = slip._get_regular_variable_computable_amount(previous_slips)

            # 4. Ajuste manual (Migración / Regularizaciones)
            monto_ajuste = slip.ajuste_remuneracion_computable or 0.0
            
            # 4. Resultado final RC_B
            slip.remuneracion_computable = fixed_computable + variable_computable + monto_ajuste
            
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
    #envio de correos de boeltas d epago Tipo: nomina
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
        
    
    
   #######################################################################
    # Envío de correos de constancia CTS
    def action_send_boleta_cts_email_employee(self):
        # Seguridad: solo usuarios autorizados pueden enviar constancias CTS
        if not self.env.user.has_group("hr_payroll_community.group_hr_payroll_community_user"):
            raise UserError(_("No tienes permisos para enviar constancias CTS."))

        # Validar que todas las boletas seleccionadas sean de tipo CTS
        invalid_slips = self.filtered(lambda slip: slip.payroll_type != 'cts')

        if invalid_slips:
            invalid_names = ", ".join(
                invalid_slips.mapped(lambda s: s.payslip_nickname or s.name or s.employee_id.name or "")
            )
            raise UserError(_(
                "La constancia CTS solo puede enviarse para boletas de tipo CTS. "
                "Revise las siguientes boletas: %s"
            ) % invalid_names)

        # Correo en copia
        email_cc = "jbernui@gerens.pe"

        email_from = (
            self.env.user.partner_id.email_formatted
            or self.env.company.partner_id.email_formatted
        )

        if not email_from:
            raise UserError(
                _("Configura un correo en el usuario actual o en la compañía.")
            )

        report_action = self.env.ref(
            "zpayroll.action_report_boleta_cts",
            raise_if_not_found=False,
        )

        if not report_action:
            raise UserError(
                _("No se encontró el reporte zpayroll.action_report_boleta_cts.")
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

            cts_name = slip.payslip_nickname or slip.name or employee_name
            filename = "Constancia CTS - %s.pdf" % cts_name
            filename = filename.replace("/", "-")

            attachment = self.env["ir.attachment"].sudo().create({
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(pdf_content),
                "res_model": slip._name,
                "res_id": slip.id,
                "mimetype": "application/pdf",
            })

            subject = "Constancia CTS - %s" % cts_name

            body_html = """
                <p>Estimado(a) %s,</p>
                <p>Adjunto encontrará su constancia de depósito semestral de CTS correspondiente.</p>
                <p>Saludos cordiales.</p>
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

        message = _("Se envió %s constancia(s) CTS.") % sent_count

        if skipped_employees:
            message += _(" No se enviaron constancias a empleados sin correo: %s") % (
                ", ".join(skipped_employees)
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Envío de constancias CTS"),
                "message": message,
                "type": "success" if sent_count else "warning",
                "sticky": True if skipped_employees else False,
            },
        }