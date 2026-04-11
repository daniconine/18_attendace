from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class EmployeeFamily(models.Model):
    _name = 'employee.family'
    _description = 'Familiares'
    
    name = fields.Char(string='Nombre Completo', required=True)
    employee_id = fields.Many2one(string="Empleado", comodel_name="hr.employee", ondelete="cascade")

    #DATOS
    relationship = fields.Selection([
        ('child', 'Hijo'),
        ('spouse', 'Cónyuge'),
        ('parent', 'Padre/Madre'),
        ('other', 'Otro'),
    ], string='Parentesco', required=True)
    vat = fields.Char(string="Nro. de identificación")
    gender = fields.Selection(string="Género", selection=[('male', 'Masculino'), ('female', 'Femenino')])
    birth_date = fields.Date(
        string='Fecha de nacimiento',
        store=True)
    age = fields.Integer(string="Edad", compute="_compute_age")

    #ASIGNACIÓN FAMILIAR
      
    is_disabled = fields.Boolean(string="Es Discapacitado")
    has_disability_pension = fields.Boolean(string="Recibe pensión por discapacidad severa")
    is_student = fields.Boolean(string="Es Estudiante")
    is_under_age = fields.Boolean(
        string="Es Menor de Edad",
        compute="_compute_is_under_age",
        store=True)
    

    def _compute_age(self):
        for record in self:
            birth_date = record.birthday
            if birth_date:
                today = fields.Date.today()
                record.age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
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