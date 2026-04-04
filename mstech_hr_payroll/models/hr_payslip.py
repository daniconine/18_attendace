# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils

from datetime import date, datetime, time
import logging

_logger = logging.getLogger(__name__)

# This will generate 16th of days
ROUNDING_FACTOR = 16


    
class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def create_payslip(self, employee, date_from, date_to):
        """
        Método para crear un payslip para un empleado en un rango de fechas
        @param employee: Empleado para el cual se va a generar el payslip
        @param date_from: Fecha de inicio de la nómina
        @param date_to: Fecha de fin de la nómina
        @return: El payslip creado
        """
        # Buscar el contrato activo del empleado dentro del rango de fechas
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('date_start', '<=', date_to),
            ('date_end', '>=', date_from),
            ('state', '=', 'open')
        ], limit=1)

        if not contract:
            raise UserError(_('No se encontró un contrato activo para el empleado %s en el periodo de fechas proporcionado.' % employee.name))

        # Crear el payslip (boleta de pago) para el empleado
        payslip = self.create({
            'employee_id': employee.id,
            'date_from': date_from,
            'date_to': date_to,
            'contract_id': contract.id,
            'state': 'draft',
            'company_id': employee.company_id.id,
        })

        # Aquí no estamos agregando las líneas al payslip (hemos eliminado esa lógica)
        # Si quieres agregar líneas en el futuro, puedes volver a usar _create_payslip_lines

        return payslip


    """#@override
    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
      
        res = []
        for contract in contracts.filtered(lambda c: c.resource_calendar_id):  #if schedule is defined
            date_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            date_to = datetime.combine(fields.Date.from_string(date_to), time.max)
            hours_per_day = contract.resource_calendar_id.hours_per_day

            work_entries = self.env['hr.work.entry'].with_context(lang="es_PE")._read_group(
                [
                    ('state', 'in', ['validated', 'draft']),
                    ('contract_id', '=', contract.id),
                    ('date_start', '>=', date_from),
                    ('date_stop', '<=', date_to)
                ],
                ['work_entry_type_id'],
                ['duration:sum'])
            
            for entry, hours in work_entries:
                vals = {
                    'name': entry.name,
                    #'sequence': ,  #skipped
                    'code': entry.code or 'NO_CODE',
                    'number_of_days': float_utils.round(ROUNDING_FACTOR * hours / hours_per_day) / ROUNDING_FACTOR,
                    'number_of_hours': hours,
                    'contract_id': contract.id,
                }
                res.append(vals)
        return res
                """
