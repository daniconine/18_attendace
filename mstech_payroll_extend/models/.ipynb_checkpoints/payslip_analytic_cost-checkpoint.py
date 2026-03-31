# mstech_payroll_extend/models/payslip_analytic_cost.py

from odoo import models, fields

class HrPayslipAnalyticCost(models.Model):
    _name = 'hr.payslip.analytic.cost'
    _description = 'Distribución de Costo de Nómina por Centro de Costo'
    _order = 'payslip_id, salary_rule_id'

    payslip_id = fields.Many2one('hr.payslip', string="Nómina", required=True, ondelete='cascade')
    payslip_line_id = fields.Many2one('hr.payslip.line', string="Línea de Nómina")
    salary_rule_id = fields.Many2one('hr.salary.rule', string="Concepto Salarial", required=True)
    
    analytic_account_id = fields.Many2one('account.analytic.account', string="Centro de Costo / Cta. Analítica", required=True)
    
    amount = fields.Monetary(string="Costo Distribuido", required=True)
    currency_id = fields.Many2one(related='payslip_id.company_id.currency_id')