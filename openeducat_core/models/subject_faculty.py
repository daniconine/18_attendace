from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.exceptions import ValidationError

class SubjectFaculty(models.Model):
    _name = "subject.faculty"
    _inherit = "mail.thread"
    _description = "Matrícula Docente"
    
    subject_id = fields.Many2one('op.subject', string= 'Asignatura',
                                 required=True)
    faculty_id = fields.Many2one('op.faculty', string= 'Docente',
                                 required=True)
    # Campos nuevos
    role = fields.Selection([
        ('principal', 'Profesor Principal'),
        ('auxiliar', 'Profesor Auxiliar'),
        ('ayuda', 'Profesor de Apoyo'),
        ('practica', 'Profesor de Práctica'),
        ('expositor', 'Expositor'),
        ('asesor', 'Asesor'),
        ('jurado', 'Jurado'),
    ], string='Rol del Docente', required=True, tracking=True)

    current_link = fields.Selection([
        ('yes', 'Sí'),
        ('no', 'No'),
    ], string='Vínculo Actual', required=True, tracking=True, default='yes')

    activity_type = fields.Selection([
        ('lectiva', 'Lectiva'),
        ('no_lectiva', 'No lectiva'),
    ], string='Tipo de Actividad del Docente', required=True, tracking=True)

    activity_detail = fields.Selection([
        ('1', 'Actividad de Docencia'),
        ('2', 'Actividad de Gestión'),
        ('3', 'Actividad de Proyección Social'),
        ('4', 'Actividad de Investigación'),
        ('5', 'Actividad de Tutoría'),
        ('7', 'Actividad de Docencia Pre-Universitaria'),
        ('8', 'Otras Actividades'),
        ('9', 'Actividad de Preparación de Clases'),
        ('10', 'Actividad de Apoyo Docencia'),
        ('11', 'Actividad Intermitente'),
    ], string='Actividad del Docente', required=True, tracking=True)
    
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
    ('unique_subject_faculty', 
     'unique(subject_id, faculty_id)', 
     'El docente ya está asignado a esta asignatura.')]
    _sql_constraints = [
        ('unique_subject_faculty', 
         'unique(subject_id, faculty_id)', 
         'El docente ya está asignado a esta asignatura con el mismo rol.')]

    @api.constrains('role', 'activity_type')
    def _check_role_activity(self):
        """Ejemplo de validación adicional personalizada."""
        for record in self:
            if record.role == 'jurado' and record.activity_type != 'no_lectiva':
                raise ValidationError(_("El rol 'Jurado' solo puede estar asociado a actividades 'No lectivas'."))