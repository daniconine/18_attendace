from odoo import models

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def custom_save_timesheet(self):
        return {'type': 'ir.actions.client', 'tag': 'reload', }
