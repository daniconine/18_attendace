from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrPayslipWorkedDays(models.Model):
    ###V16-
    #_inherit = 'hr.payslip.worked_days'
    #V18+
    _inherit = 'hr.payslip.worked.days'

    work_entry_type_id = fields.Many2one(string="Tipo de entrada", comodel_name="hr.work.entry.type", required=True)
