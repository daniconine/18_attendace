from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ZPeriod(models.Model):
    _name = "zperiod"
    _description = "Ampliación de Zperiod"
    _inherit = ["zperiod"]
    
    # Método para crear el payslip utilizando action_compute_sheet
    def create_payslip_from_zperiod(self):
        """Este método crea el payslip utilizando el método de action_compute_sheet"""
        payslips_created = []  # Lista para almacenar los payslips creados
        
        for period in self:
            # Obtener el nombre del empleado
            employee_name = period.employee_id.name

            # Obtener el mes y el año del periodo
            month_number = period.month  # '01', '02', etc.
            year = fields.Date.from_string(period.date_end).year  # Año de 'date_end'

            # Diccionario de meses en español
            months_in_spanish = {
                '01': 'ENERO', '02': 'FEBRERO', '03': 'MARZO', '04': 'ABRIL',
                '05': 'MAYO', '06': 'JUNIO', '07': 'JULIO', '08': 'AGOSTO',
                '09': 'SEPTIEMBRE', '10': 'OCTUBRE', '11': 'NOVIEMBRE', '12': 'DICIEMBRE'}

            # Obtener el nombre del mes en español
            month_name = months_in_spanish.get(month_number, 'Mes no válido')

            # Generar el nombre del payslip con el formato solicitado
            payslip_name = f"Nomina//{employee_name}/({year}-{month_name})"

            # Buscar el contrato activo del empleado dentro del rango de fechas
            contract = self.env['hr.contract'].search([ 
                ('employee_id', '=', period.employee_id.id),
                ('date_start', '<=', period.date_end),
                ('date_end', '>=', period.date_start),
                ('state', '=', 'open')
            ], limit=1)

            if not contract:
                raise UserError(_('No se encontró un contrato activo para el empleado %s en el periodo de fechas proporcionado.' % period.employee_id.name))

            # Obtener la estructura salarial del contrato
            salary_structure = contract.struct_id
            
            # Crear el payslip (boleta de pago) para el empleado
            payslip = self.env['hr.payslip'].create({
                'employee_id': period.employee_id.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'contract_id': contract.id,
                'state': 'draft',
                'company_id': period.employee_id.company_id.id,
                'name': payslip_name,  # Asignar el nombre generado en ZPeriod
                'struct_id': salary_structure.id,  # Asignar la estructura salarial al payslip

            })
            
            #---Aqui va la insercion delineas woekdays e inputs)---#
            # Crear línea de "inasistencia" en el payslip
            if period.days_unattended > 0:
                self.env['hr.payslip.worked.days'].create({
                    'payslip_id': payslip.id,
                    'name': 'Inasistencias',
                    'code': 'UNATTENDED',
                    'number_of_days': period.days_unattended,
                    'number_of_hours': period.days_unattended * 8,  # Suponiendo 8 horas por día de inasistencia
                    'contract_id': contract.id,
                })

            
            #---Fin de insercion--#
            
            
            # Llamar al método action_compute_sheet para calcular las líneas del payslip
            payslip.action_compute_sheet()

            # Notificar sobre la creación
            if payslip:
                self.message_post(body="Payslip creado con éxito para el empleado %s en el periodo %s - %s" % (
                    period.employee_id.name, period.date_start, period.date_end),
                                  message_type='notification')
            
            # Agregar el payslip a la lista de los creados
            payslips_created.append(payslip)

        # Retornar todos los payslips creados al finalizar el ciclo
        return payslips_created