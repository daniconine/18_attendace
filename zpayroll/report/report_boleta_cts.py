# -*- coding: utf-8 -*-

from datetime import date

from odoo import models, _
from odoo.exceptions import UserError


class ReportBoletaCTS(models.AbstractModel):
    _name = 'report.zpayroll.report_boleta_cts_document'
    _description = 'Reporte Boleta CTS'

    def _get_employee_extension(self, employee):
        if not employee:
            return False

        return self.env['zemployee.extension'].sudo().search([
            ('employee_id', '=', employee.id)
        ], limit=1)

    def _safe_get(self, record, field_name, default=False):
        """
        Permite leer campos opcionales sin romper el reporte
        si el campo no existe todavía en zemployee.extension u otro modelo.
        """
        if not record:
            return default

        if field_name in record._fields:
            return record[field_name]

        return default

    def _validate_cts_payslips(self, payslips):
        invalid_slips = payslips.filtered(lambda p: p.payroll_type != 'cts')

        if invalid_slips:
            names = ', '.join(invalid_slips.mapped('name'))
            raise UserError(_(
                "La constancia CTS solo puede generarse para boletas de tipo CTS. "
                "Revise las siguientes boletas: %s"
            ) % names)

    def _get_cts_period_data(self, payslip):
        """
        Define el semestre CTS según el mes de la boleta:
        - Mayo: noviembre del año anterior a abril del año actual.
        - Noviembre: mayo a octubre del año actual.
        """
        month = payslip.payroll_month_number or 0

        try:
            year = int(payslip.payroll_year or 0)
        except Exception:
            year = 0

        if month == 5 and year:
            date_from = date(year - 1, 11, 1)
            date_to = date(year, 4, 30)
            label = "Del 01-11-%s al 30-04-%s" % (year - 1, year)

        elif month == 11 and year:
            date_from = date(year, 5, 1)
            date_to = date(year, 10, 31)
            label = "Del 01-05-%s al 31-10-%s" % (year, year)

        else:
            date_from = False
            date_to = False
            label = ""

        return {
            'date_from': date_from,
            'date_to': date_to,
            'label': label,
            'months': 6,
            'days': 0,
        }

    def _sum_lines_by_codes(self, payslip, codes):
        lines = payslip.line_ids.filtered(
            lambda l: l.salary_rule_id.code in codes or l.code in codes
        )
        return sum(lines.mapped('total'))

    def _get_gratificacion_for_cts(self, payslip):
        """
        Para CTS mayo: toma GRATI_DICIEMBRE del año anterior.
        Para CTS noviembre: toma GRATI_JULIO del mismo año.
        """
        month = payslip.payroll_month_number or 0

        try:
            year = int(payslip.payroll_year or 0)
        except Exception:
            year = 0

        if not year:
            return {
                'gratificacion': 0.0,
                'sexto_gratificacion': 0.0,
                'grati_code': False,
            }

        grati_code = False
        grati_year = False
        grati_month = False

        if month == 5:
            grati_code = 'GRATI_DICIEMBRE'
            grati_year = str(year - 1)
            grati_month = 12

        elif month == 11:
            grati_code = 'GRATI_JULIO'
            grati_year = str(year)
            grati_month = 7

        gratificacion = 0.0

        if grati_code:
            grati_slip = self.env['hr.payslip'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('payroll_year', '=', grati_year),
                ('payroll_month_number', '=', grati_month),
                ('state', '!=', 'cancel'),
            ], order='date_to desc, write_date desc, id desc', limit=1)

            if grati_slip:
                gratificacion = self._sum_lines_by_codes(grati_slip, [grati_code])

        return {
            'gratificacion': gratificacion,
            'sexto_gratificacion': gratificacion / 6.0 if gratificacion else 0.0,
            'grati_code': grati_code,
        }

    def _get_previous_nomina_slips_for_cts(self, payslip):
        """
        Reutiliza el método del payslip si ya existe.
        Para CTS mayo, tomando date_to de mayo, trae abril a noviembre.
        Para CTS noviembre, tomando date_to de noviembre, trae octubre a mayo.
        """
        if hasattr(payslip, '_get_previous_nomina_slips_by_month'):
            return payslip._get_previous_nomina_slips_by_month(payslip, months=6)

        return self.env['hr.payslip'].browse()

    def _get_regular_variable_breakdown(self, payslip):
        """
        Calcula variables computables regulares del semestre.
        La regularidad se evalúa por regla salarial: 3 o más meses.
        Luego clasifica en:
        - Comisiones
        - Horas extras
        - Otros conceptos regulares
        """
        previous_slips = self._get_previous_nomina_slips_for_cts(payslip)

        variable_data = {}

        for previous_slip in previous_slips:
            variable_lines = previous_slip.line_ids.filtered(
                lambda l: l.salary_rule_id.is_computable
                and l.salary_rule_id.is_variable
                and l.total > 0
            )

            monthly_rules = {}

            for line in variable_lines:
                rule = line.salary_rule_id
                code = rule.code or line.code or str(rule.id)

                if code not in monthly_rules:
                    monthly_rules[code] = {
                        'name': rule.name,
                        'code': code,
                        'amount': 0.0,
                    }

                monthly_rules[code]['amount'] += line.total

            for code, data in monthly_rules.items():
                if code not in variable_data:
                    variable_data[code] = {
                        'name': data['name'],
                        'code': data['code'],
                        'total': 0.0,
                        'months': 0,
                    }

                variable_data[code]['total'] += data['amount']
                variable_data[code]['months'] += 1

        comisiones = 0.0
        horas_extras = 0.0
        otros_regulares = 0.0

        for code, data in variable_data.items():
            if data['months'] < 3:
                continue

            promedio = data['total'] / 6.0
            code_upper = (code or '').upper()
            name_upper = (data['name'] or '').upper()

            if 'COMISION' in code_upper or 'COMISIÓN' in name_upper or 'COMISION' in name_upper:
                comisiones += promedio

            elif (
                'HRS' in code_upper
                or 'HORA_EXTRA' in code_upper
                or 'HORAS EXTRA' in name_upper
                or 'HORAS EXTRAS' in name_upper
            ):
                horas_extras += promedio

            else:
                otros_regulares += promedio

        return {
            'comisiones': comisiones,
            'horas_extras': horas_extras,
            'otros_regulares': otros_regulares,
        }

    def _get_cts_line_amount(self, payslip):
        """
        Busca el monto CTS calculado en la boleta.
        Soporta CTS_MAYO, CTS_NOVIEMBRE o una regla genérica CTS.
        """
        cts_codes = ['CTS_MAYO', 'CTS_NOVIEMBRE', 'CTS']

        amount = self._sum_lines_by_codes(payslip, cts_codes)

        return amount

    def _get_cts_report_data(self, payslip):
        employee = payslip.employee_id
        contract = payslip.contract_id
        company = payslip.company_id
        ext = self._get_employee_extension(employee)

        period_data = self._get_cts_period_data(payslip)
        grati_data = self._get_gratificacion_for_cts(payslip)
        variable_data = self._get_regular_variable_breakdown(payslip)

        basico = contract.wage or 0.0

        asignacion_familiar = 0.0
        if employee and employee.has_family_allowance():
            asignacion_familiar = (payslip.rmv or 0.0) * 0.10

        alimentacion_principal = 0.0

        bonificaciones = 0.0
        if contract:
            bonificaciones += contract.bono_fijo_computable_mensual or 0.0
            bonificaciones += contract.concepto_fijo_computable_mensual or 0.0

        comisiones = variable_data['comisiones']
        horas_extras = variable_data['horas_extras']
        gratificaciones = grati_data['sexto_gratificacion']

        # La RC_B ya contiene sueldo + asignación + fijos + variables regulares.
        # Para CTS se suma 1/6 de gratificación.
        total_remuneracion_cts = (
            (payslip.remuneracion_computable or 0.0)
            + gratificaciones
        )

        subtotal_detalle = (
            basico
            + asignacion_familiar
            + alimentacion_principal
            + bonificaciones
            + comisiones
            + horas_extras
            + gratificaciones
        )

        otros_regulares = total_remuneracion_cts - subtotal_detalle

        if abs(otros_regulares) < 0.01:
            otros_regulares = 0.0

        monto_cts = self._get_cts_line_amount(payslip)

        if not monto_cts:
            monto_cts = total_remuneracion_cts / 12.0 * period_data['months']

        banco_cts = (
            self._safe_get(ext, 'cts_bank_id', False).name
            if self._safe_get(ext, 'cts_bank_id', False)
            else ''
        )

        cuenta_cts = self._safe_get(ext, 'cts_account_number', '') or ''
        moneda_cts = self._safe_get(ext, 'cts_currency_id', False)
        moneda_cts_name = moneda_cts.name if moneda_cts else company.currency_id.name

        return {
            'company': {
                'name': company.name,
                'vat': company.vat or '',
                'street': company.street or '',
                'city': company.city or '',
                'representative': '',
            },
            'employee': {
                'name': employee.name or '',
                'identification_id': employee.identification_id or '',
                'job_title': employee.job_title or '',
            },
            'period': period_data,
            'deposit': {
                'date': payslip.date_to,
                'bank': banco_cts,
                'account': cuenta_cts,
                'currency': moneda_cts_name,
                'amount': monto_cts,
            },
            'cts': {
                'basico': basico,
                'asignacion_familiar': asignacion_familiar,
                'alimentacion_principal': alimentacion_principal,
                'bonificaciones': bonificaciones,
                'comisiones': comisiones,
                'horas_extras': horas_extras,
                'gratificaciones': gratificaciones,
                'otros_regulares': otros_regulares,
                'total_remuneracion_computable': total_remuneracion_cts,
                'monto_cts': monto_cts,
            },
        }

    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.payslip'].browse(docids)

        self._validate_cts_payslips(docs)

        report_data_by_id = {}

        for payslip in docs:
            report_data_by_id[payslip.id] = self._get_cts_report_data(payslip)

        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'report_data_by_id': report_data_by_id,
        }