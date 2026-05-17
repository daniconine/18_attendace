from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class EmployeeFamily(models.Model):
    _name = 'employee.family'
    _description = 'Familiares'
    
    name = fields.Char(string='Nombre del Familiar', required=True)
    zemployee_extension_id = fields.Many2one(
        'zemployee.extension',
        string='Empleado Z',
        required=True,
        ondelete='cascade'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='zemployee_extension_id.company_id',
        store=True,
        readonly=True)

    #DATOS
    relationship = fields.Selection([
        ('child', 'Hijo(a)'),
        ('spouse', 'Cónyuge'),
        ('parent', 'Padre/Madre'),
        ('other', 'Otro'),
    ], string='Parentesco', required=True)
    vat_dni = fields.Char(string="Nro. de identificación (DNI)")
    gender = fields.Selection(string="Género", selection=[('male', 'Masculino'), ('female', 'Femenino')])
    birth_date = fields.Date(string='Fecha de nacimiento', store=True)
    age = fields.Integer(string="Edad", compute="_compute_age")

    #ASIGNACIÓN FAMILIAR
      
    is_disabled = fields.Boolean(string="Es Discapacitado")
    has_disability_pension = fields.Boolean(string="Recibe pensión por discapacidad severa")
    is_student = fields.Boolean(string="Es Estudiante Universitario")
    is_under_age = fields.Boolean(
        string="Es Menor de Edad",
        compute="_compute_is_under_age",
        store=True)
    

    @api.depends('birth_date')
    def _compute_age(self):
        today = fields.Date.today()
        for record in self:
            if record.birth_date:
                record.age = (
                    today.year
                    - record.birth_date.year
                    - ((today.month, today.day) < (record.birth_date.month, record.birth_date.day))
                )
            else:
                record.age = 0
    
    #calculo para ver si es menor de edad
    @api.depends('birth_date')
    def _compute_is_under_age(self):
        today = fields.Date.today()
        for record in self:
            if record.birth_date:
                age = (
                    today.year
                    - record.birth_date.year
                    - ((today.month, today.day) < (record.birth_date.month, record.birth_date.day))
                )
                record.is_under_age = age < 18
            else:
                record.is_under_age = False