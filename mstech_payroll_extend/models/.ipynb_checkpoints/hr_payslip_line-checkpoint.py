from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    plame_code = fields.Char(string="Código concepto (PLAME)", size=4)