# mstech_payroll_extend/models/res_bank.py

from odoo import models, fields

class ResBank(models.Model):
    _inherit = 'res.bank'

    payment_file_template_id = fields.Many2one(
        'hr.report.template',
        string="Plantilla para Pago Masivo",
        help="Selecciona la plantilla de reporte que se usará para generar el archivo de pago para este banco."
    )