# mstech_payroll_extend/models/commission.py

from odoo import models, fields

class HrCommission(models.Model):
    _name = 'hr.commission'
    _description = 'Comisión Generada'
    _order = 'date desc'
    _rec_name = 'employee_id'

    config_id = fields.Many2one('hr.commission.config', string="Plan de Origen", readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    amount = fields.Monetary(string="Monto Comisión", required=True, currency_field='company_currency_id')
    date = fields.Date(string="Fecha Comisión", required=True)

    # --- TRAZABILIDAD (Tu Lógica Desacoplada) ---
    res_model = fields.Char(string='Modelo de Origen', readonly=True)
    res_id = fields.Integer(string='ID de Origen', readonly=True)

    # --- DATOS FINANCIEROS ORIGINALES ---
    source_amount = fields.Monetary(string="Monto Base Original", currency_field='source_currency_id')
    source_currency_id = fields.Many2one('res.currency', string="Moneda Original")
    
    # ➤ NUEVO CAMPO: TASA DE CAMBIO
    exchange_rate = fields.Float(
        string="Tasa de Cambio Aplicada", 
        digits=(12, 6), 
        readonly=True,
        help="La tasa de cambio usada para convertir el monto original a la moneda de la compañía, si fue necesario."
    )

    # --- ESTADO Y PAGO ---
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Liquidada'), ('cancel', 'Cancelada')], default='draft', readonly=True)
    payslip_id = fields.Many2one('hr.payslip', string="Boleta de Pago", readonly=True)

    company_id = fields.Many2one('res.company', string='Compañía', related='employee_id.company_id', store=True)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    def action_open_source_document(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }