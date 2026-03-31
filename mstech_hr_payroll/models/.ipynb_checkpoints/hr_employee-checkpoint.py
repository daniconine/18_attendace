# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class EmployeeRelative(models.Model) :
    _name = 'employee.relative'
    _description = 'Familiar'
    
    name = fields.Char(string='Nombre Completo', required=True)
    employee_id = fields.Many2one(string="Empleado", comodel_name="hr.employee", ondelete="cascade")

    #DATOS
    relationship = fields.Char(string="Parentesco")
    vat = fields.Char(string="Nro. de identificación")
    gender = fields.Selection(string="Género", selection=[('male', 'Masculino'), ('female', 'Femenino')])
    birthday = fields.Date(string="Fecha de nacimiento")
    age = fields.Integer(string="Edad", compute="_compute_age")

    #ASIGNACIÓN FAMILIAR
    is_child = fields.Boolean(string="Hijo")
    is_disabled = fields.Boolean(string="Discapacitado")
    has_disability_pension = fields.Boolean(string="Recibe pensión por discapacidad severa")
    is_student = fields.Boolean(string="Estudiante")

    def _compute_age(self):
        for record in self:
            birth_date = record.birthday
            if birth_date:
                today = fields.Date.today()
                record.age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            else:
                record.age = 0


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    cuspp = fields.Char(string="CUSPP (PE)", tracking=True)
    is_not_resident = fields.Boolean(string="No es residente")

    relative_ids = fields.One2many(string="Familiares (PE)", comodel_name="employee.relative", inverse_name="employee_id")
    children = fields.Integer(string="Número de hijos dependientes", compute="_compute_children_count", store=True, readonly=True)
    disabled_children = fields.Integer(string="Número de hijos con discapacidad", compute="_compute_children_count", store=True, readonly=True)
    student_children = fields.Integer(string="Número de hijos estudiantes", compute="_compute_children_count", store=True, readonly=True)

    @api.depends('relative_ids', 'relative_ids.is_child', 'relative_ids.is_disabled', 'relative_ids.is_student')
    def _compute_children_count(self):
        for record in self:
            to_write = {
                'children': 0,
                'disabled_children': 0,
                'student_children': 0,
            }
            for relative in record.relative_ids:
                if relative.is_child:
                    to_write['children'] += 1
                    if relative.is_disabled:
                        to_write['disabled_children'] += 1
                    if relative.is_student:
                        to_write['student_children'] += 1
            record.write(to_write)
