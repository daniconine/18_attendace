from odoo import models, fields, api
from datetime import datetime

class ZVacationYear(models.Model):
    _name = 'zleave.zvacation.year'
    _description = 'Acumulación de Vacaciones Anual'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    year = fields.Char(string='Año')
    start_date = fields.Date(string='Fecha inicial Acumulación', default=fields.Date.today)
    end_date = fields.Date(string='Fecha final Acumulación' )
    accumulated_days = fields.Float(string='Días Acumulados')
    consumed_days = fields.Float(string='Días Consumidos')
    closed = fields.Boolean(string='Acumulación cerrada', default=False)
    vacation_id = fields.Many2one('zleave.zvacation', string='Solicitud de Vacaciones', ondelete='cascade')
    balance_days = fields.Float(string='Saldo')