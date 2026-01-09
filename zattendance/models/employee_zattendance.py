##########################################################
## Modelo agrega funcionalaidad para zatteendnace

from odoo import models, fields, api
from datetime import datetime, timedelta, time

class EmployeeWeeklySchedule(models.Model):
    _name = 'employee.weekly.schedule'
    _description = 'Horario Semanal de Empleado'

    employee_id = fields.Many2one(
        'hr.employee',
        string="Empleado",
        required=True,
        ondelete='cascade',
    )

    day_of_week = fields.Selection([
        ('monday', 'Lunes'),
        ('tuesday', 'Martes'),
        ('wednesday', 'Miércoles'),
        ('thursday', 'Jueves'),
        ('friday', 'Viernes'),
        ('saturday', 'Sábado'),
        ('sunday', 'Domingo'),
    ], string="Día de la Semana", required=True)

    # horas en float
    start_time = fields.Float(
        string="Hora de Entrada",
        required=True,
        help="Hora de entrada en formato 24h (ej. 9.5 = 09:30)"
    )
    end_time = fields.Float(
        string="Hora de Salida",
        required=True,
        help="Hora de salida en formato 24h (ej. 19.0 = 19:00)"
    )

    # aquí usas el mismo tipo que en zattendance.day
    planned_attendance_type = fields.Selection(
        [
            ("presencial", "Presencial"),
            ("virtual", "Teletrabajo"),
            ("descanso", "Descanso"),
            ("feriado", "Feriado"),
            ("vacaciones", "Vacaciones"),
            ("lic_con_goce", "Lic. con goce"),
            ("lic_sin_goce", "Lic. sin goce"),
            ("confianza", "Confianza"),
        ],
        string="Tipo de Asistencia",
        required=True,
    )

    start_date = fields.Date(string="Fecha Inicial", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
