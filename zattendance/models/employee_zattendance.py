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

    signature_image = fields.Binary("Firma Digital", attachment=True)

    @api.model
    def create(self, vals):
        # Procesar la firma al crear un nuevo empleado
        if vals.get('signature_image'):
            vals['signature_image'] = self._process_signature(vals['signature_image'])
        return super(Employee, self).create(vals)

    def write(self, vals):
        # Procesar la firma al actualizar un empleado
        if vals.get('signature_image'):
            vals['signature_image'] = self._process_signature(vals['signature_image'])
        return super(Employee, self).write(vals)

    def _process_signature(self, signature_image):
        """Valida y procesa la imagen de la firma"""
        # Decodificar la imagen de base64 a un objeto de imagen
        image_data = base64.b64decode(signature_image)
        image = Image.open(io.BytesIO(image_data))

        # Validar formato (PNG recomendado)
        if image.format != 'PNG':
            raise UserError("La firma debe estar en formato PNG.")

        # Redimensionar la imagen a un tamaño estándar
        image = image.resize((300, 150))  # Tamaño estandarizado (300x150 píxeles)

        # Comprimir la imagen (ajustar calidad si es necesario)
        byte_io = io.BytesIO()
        image.save(byte_io, format='PNG', quality=85)  # Ajustar calidad si es necesario
        byte_io.seek(0)

        # Volver a codificar la imagen a base64
        processed_image = base64.b64encode(byte_io.read())
        return processed_image