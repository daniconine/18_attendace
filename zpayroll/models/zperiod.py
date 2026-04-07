from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ZPeriod(models.Model):
  
    _inherit = ["zperiod"]
    
    # Método para crear el payslip utilizando action_compute_sheet
    def create_payslip_from_zperiod(self):
        payslips_created = []

        months_in_spanish = {
            '01': 'ENERO', '02': 'FEBRERO', '03': 'MARZO', '04': 'ABRIL',
            '05': 'MAYO', '06': 'JUNIO', '07': 'JULIO', '08': 'AGOSTO',
            '09': 'SEPTIEMBRE', '10': 'OCTUBRE', '11': 'NOVIEMBRE', '12': 'DICIEMBRE'
        }

        for period in self:
            employee_name = period.employee_id.name or ''
            month_number = str(period.month or '').zfill(2)
            year = fields.Date.from_string(period.date_end).year
            month_name = months_in_spanish.get(month_number, 'MES')

            payslip_name = f"Nomina//{employee_name}/({year}-{month_name})"

            contract = self.env['hr.contract'].search([
                ('employee_id', '=', period.employee_id.id),
                ('date_start', '<=', period.date_end),
                ('state', '=', 'open'),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', period.date_start),
            ], limit=1)

            if not contract:
                raise UserError(_(
                    'No se encontró un contrato activo para el empleado %s en el periodo de fechas proporcionado.'
                ) % period.employee_id.name)

            salary_structure = contract.struct_id
            if not salary_structure:
                raise UserError(_(
                    'El contrato del empleado %s no tiene estructura salarial configurada.'
                ) % period.employee_id.name)

            payslip = self.env['hr.payslip'].create({
                'employee_id': period.employee_id.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'contract_id': contract.id,
                'state': 'draft',
                'company_id': period.employee_id.company_id.id,
                'name': payslip_name,
                'struct_id': salary_structure.id,
            })

            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Inasistencias',
                'code': 'UNATTENDED',
                'number_of_days': period.days_unattended or 0.0,
                'number_of_hours': (period.days_unattended or 0.0) * 8,
                'contract_id': contract.id,
            })

            payslip.action_compute_sheet()

            period.message_post(
                body="Payslip creado con éxito para el empleado %s en el periodo %s - %s" % (
                    period.employee_id.name, period.date_start, period.date_end
                ),
                message_type='notification'
            )

            payslips_created.append(payslip)

        return payslips_created