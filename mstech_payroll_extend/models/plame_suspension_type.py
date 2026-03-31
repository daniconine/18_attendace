# mstech_payroll_extend/models/plame_suspension_type.py

from odoo import models, fields

class HrPlameSuspensionType(models.Model):
    _name = 'hr.plame.suspension.type'
    _description = 'PLAME: Tipos de Suspensión de Labores'
    _order = 'code'

    code = fields.Char(string='Código SUNAT', required=True, size=2)
    name = fields.Char(string='Descripción SUNAT', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'El código SUNAT debe ser único.')
    ]