from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    uit = fields.Float(string='UIT',default=5500.0)
    rmv = fields.Float(string='RMV', default=1130.0)
    onp_rate = fields.Float(string='% ONP', default=13.0)
    essalud_rate = fields.Float(string='% EsSalud', default=9.0)
    eps = fields.Float(string='% EPS', default=2.25)
    eps_essalud_rate = fields.Float(string='% EPS EsSalud', default=6.75)
    
    payroll_month = fields.Selection([
        ('01', 'ENERO'),
        ('02', 'FEBRERO'),
        ('03', 'MARZO'),
        ('04', 'ABRIL'),
        ('05', 'MAYO'),
        ('06', 'JUNIO'),
        ('07', 'JULIO'),
        ('08', 'AGOSTO'),
        ('09', 'SEPTIEMBRE'),
        ('10', 'OCTUBRE'),
        ('11', 'NOVIEMBRE'),
        ('12', 'DICIEMBRE'),
    ], string='Mes', compute='_compute_payroll_month', store=True)
    

    @api.depends('date_to')
    def _compute_payroll_month(self):
        for slip in self:
            if slip.date_to:
                slip.payroll_month = str(slip.date_to.month).zfill(2)
            else:
                slip.payroll_month = False