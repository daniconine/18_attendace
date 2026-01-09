from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OpCourse(models.Model):
    _name = "op.course"
    _inherit = "mail.thread"
    _description = "Programa"

    name = fields.Char('Name', required=True)
    code_system = fields.Char('Code CCA', required=True)
    code_siu_local = fields.Char('Code SIU Local')
    code_siu_program = fields.Char('Code SIU Programa')
    code_siu_facultad = fields.Char('Code SIU Facultad')
    parent_id = fields.Many2one('op.course', 'Programa Relacionado')
   
    subject_ids = fields.One2many('op.subject', 'course_id', string='Cursos/Asignaturas')
    max_unit_load = fields.Float("Maximo N° inscritos")
    min_unit_load = fields.Float("Minimo N° inscritos")
    department_id = fields.Many2one(
        'op.department', 'Department',
        default=lambda self:
        self.env.user.dept_id and self.env.user.dept_id.id or False)
    active = fields.Boolean(default=True)
    
    
    start_date = fields.Date('Fecha de Inicio', required=True)
    end_date = fields.Date('Fecha de Fin', required=True)
    area = fields.Selection([
        ('maestria', 'Maestria'),
        ('cap_continua', 'Capacitación Ejecutiva'),
        ('cap_corporativa', 'Capacitación Corporativa'),
        ('otros', 'Otra Area')
    ], string='Area', required=True)
    state = fields.Selection([
        ('activo', 'Activo'),
        ('terminado', 'Terminado'),
        ('no_iniciado', 'Por Iniciar')
    ], string='Estado', required=True)
    number_cycle = fields.Selection([
        ('0', 'Unico Ciclo'),
        ('1', 'Dos Ciclos'),
        ('2', 'Cuatro Ciclos'),
        ('3', 'Otro')
    ], string='N° Ciclos')
    
    
    _sql_constraints = [
        ('unique_course_code',
         'unique(code)', 'Code should be unique per course!')]

    @api.constrains('parent_id')
    def _check_parent_id_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive Course.'))
        return True

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Courses'),
            'template': '/openeducat_core/static/xls/op_course.xls'
        }]
