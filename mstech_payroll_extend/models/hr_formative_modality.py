# mstech_payroll_extend/models/hr_afp_rate.py

from odoo import models, fields


class hHrFormativeModality(models.Model):
    _name = 'hr.formative.modality'
    _description = 'Modalidad Formativa'

    name = fields.Char(string="Descripción")
    code = fields.Char(string="Código", size=2)
