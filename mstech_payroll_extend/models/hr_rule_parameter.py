# mstech_payroll_extend/models/hr_rule_parameter.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrRuleParameter(models.Model):
    _name = 'hr.rule.parameter'
    _description = 'Parámetros para Reglas Salariales'

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código", required=True, help="Código usado en las reglas salariales para llamar a este parámetro.")
    description = fields.Text(string="Descripción")
    
    version_ids = fields.One2many(
        'hr.rule.parameter.version',
        'parameter_id',
        string="Versiones"
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'El código del parámetro debe ser único.')
    ]

class HrRuleParameterVersion(models.Model):
    _name = 'hr.rule.parameter.version'
    _description = 'Versión de Parámetro de Regla Salarial'
    _order = 'date_from desc'

    parameter_id = fields.Many2one('hr.rule.parameter', ondelete='cascade', required=True)
    date_from = fields.Date(string="Desde", required=True)
    value = fields.Float(string="Valor de parámetro", digits='Payroll', required=True)
