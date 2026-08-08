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
            
            if period.state != "open":
                raise UserError(_(
                    "El periodo del empleado %s no está abierto. No se puede generar nomina desde este periodo"
                ) % period.employee_id.name)
                
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

            ##########Bloque de ingreso de Insumos
            #####Regla ASistencias
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Asistencias',
                'code': 'WORK100',
                'number_of_days': period.days_attended or 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,})
            
            #####Regla Licencia Con Goce / Permiso
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Licencia Con Goce / Permiso',
                'code': 'PERMISO',
                'number_of_days': period.days_permissions or 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })

            #####Regla Licencia Sin Goce / Ausencia
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Licencia Sin Goce / Ausencia',
                'code': 'AUSENCIA',
                'number_of_days': period.days_leave_permissions or 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            
            #####Regla Vacaciones
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Vacaciones Devengadas',
                'code': 'VAC',
                'number_of_days': period.days_vacations or 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,})
            
            #####Regla Inasistencia
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Inasistencias',
                'code': 'FALTAS',
                'number_of_days': period.days_unattended or 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,})
            
            #####Horas Extras al 25%
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Horas Extras 25%',
                'code': 'hrs_25',
                'number_of_days': 0.0,
                'number_of_hours': period.hrs_25 or 0.0,
                'contract_id': contract.id,})
            
            #####Horas Extras al 35%
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Horas Extras 35%',
                'code': 'hrs_35',
                'number_of_days': 0.0,
                'number_of_hours': period.hrs_35 or 0.0,
                'contract_id': contract.id,})

            #####Horas Extras al 100%
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Horas Extras 100%',
                'code': 'hrs_100',
                'number_of_days': 0.0,
                'number_of_hours': period.hrs_100 or 0.0,
                'contract_id': contract.id,})
            
            #####Horas Extras al 200%
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Horas Extras 200%',
                'code': 'hrs_200',
                'number_of_days': 0.0,
                'number_of_hours': period.hrs_200 or 0.0,
                'contract_id': contract.id,})
            
            # Calculamos la conversión de minutos a horas
            horas_tardanza = period.late_min_total / 60.0 if period.late_min_total else 0.0

            ###########tardanzas
            self.env['hr.payslip.worked.days'].create({
                'payslip_id': payslip.id,
                'name': 'Tardanzas',
                'code': 'TARDE',
                'number_of_days': 0.0,
                'number_of_hours': horas_tardanza,
                'contract_id': contract.id,})
            
            
            ###otras Entradas
            ###########Bonos con estrcutura para cada bono aparezca como una linea separada
            """for bono in period.bonus_ids:
                self.env['hr.payslip.input'].create({
                    'payslip_id': payslip.id,
                    'name': bono.note or 'Bono',
                    'code': 'BONO',
                    'amount': bono.amount,
                    'contract_id': contract.id,
                })"""
                
            ###########Bonos con estrcutura ideal para una sola linea   
            # Sumamos el campo 'amount' de todos los registros en 'bonus_ids'
            total_bonos = sum(period.bonus_ids.mapped('amount'))

            #####Entrada de Bonos
            self.env['hr.payslip.input'].create({
                'payslip_id': payslip.id,
                'name': 'Bonos del Periodo',
                'code': 'BONO',                
                'amount': total_bonos,
                'contract_id': contract.id,})
            
            # Sumamos el campo 'amount' de todos los registros de comisiones
            total_comisiones = sum(period.commission_ids.mapped('amount'))

            #####Entrada de Comisiones
            self.env['hr.payslip.input'].create({
                'payslip_id': payslip.id,
                'name': 'Comisiones del Periodo',
                'code': 'COMISION',                
                'amount': total_comisiones,
                'contract_id': contract.id,})
            
            # Sumamos el campo 'amount' de todos los registros de disctado de clases
            total_dictado_clases = sum(period.class_line_ids.mapped('amount'))

            #####Entrada de Claes
            self.env['hr.payslip.input'].create({
                'payslip_id': payslip.id,
                'name': 'Dictado de Clases del Periodo',
                'code': 'CLASES',                
                'amount': total_dictado_clases,
                'contract_id': contract.id,})
            
            # Entradas manuales que deben quedar disponibles en la nómina
            manual_input_lines = [{'name': 'Descuento EPS Trabajador','code': 'DESC_EPS',},
                            {'name': 'Préstamo Tercero a Trabajador','code': 'PRESTAMO_TRAB',},
                            {'name': 'Préstamo GERENS a Trabajador','code': 'PRESTAMO_GERENS',},
                            {'name': 'Otros Descuentos','code': 'Desc_OTROS',},]

            #####Entrada de descuentos en la nomina
            for input_data in manual_input_lines:
                self.env['hr.payslip.input'].create({
                    'payslip_id': payslip.id,
                    'name': input_data['name'],
                    'code': input_data['code'],
                    'amount': 0.0,
                    'contract_id': contract.id,
                })
            
            payslip.action_compute_sheet() #3ejecucion

            period.message_post(
                body="Payslip creado con éxito para el empleado %s en el periodo %s - %s" % (
                    period.employee_id.name, period.date_start, period.date_end),
                message_type='notification')

            period.write({"state": "closed",})
            payslips_created.append(payslip)

        return payslips_created