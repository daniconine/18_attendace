from odoo import models, fields, api
from odoo.exceptions import UserError

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    type_id = fields.Many2one(string="Tipo", comodel_name="hr.payroll.structure.type")
