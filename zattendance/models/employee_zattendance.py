##########################################################
## Modelo agrega funcionalaidad para zatteendnace y empelado
from odoo import models, fields, api
from PIL import Image
import io
import base64
from odoo.exceptions import UserError 

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


class Employee(models.Model):
    _inherit = 'hr.employee'

    _sql_constraints = [(
            'unique_work_email_company',
            'unique(work_email, company_id)',
            'El correo del empleado ya está registrado en esta compañía.'),]

    