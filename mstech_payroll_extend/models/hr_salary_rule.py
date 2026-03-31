from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    plame_code = fields.Char(string="Código concepto (PLAME)", size=4)