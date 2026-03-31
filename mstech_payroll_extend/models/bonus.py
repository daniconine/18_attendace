from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrBonus(models.Model):
    _name = 'hr.bonus'
    _description = 'Bono de Empleado'
    _order = 'date desc'

    name = fields.Char(string="Referencia", compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    config_id = fields.Many2one('hr.bonus.config', string="Plantilla de Bono", ondelete='restrict', required=True)
    
    # --- Campos heredados de la config para fácil acceso ---
    payslip_description = fields.Char(related='config_id.payslip_description', readonly=True)
    payslip_code = fields.Char(related='config_id.payslip_code', readonly=True)
    
    amount = fields.Monetary(string="Monto", required=True)
    currency_id = fields.Many2one(related='employee_id.company_id.currency_id')
    date = fields.Date(string="Fecha del Bono", required=True, default=fields.Date.context_today)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Incluido en Nómina'),
        ('cancel', 'Cancelado'),
    ], string="Estado", default='draft', readonly=True, copy=False)
    
    payslip_id = fields.Many2one('hr.payslip', string="Boleta de Pago", readonly=True, copy=False)

    @api.depends('config_id.name', 'employee_id.name', 'date')
    def _compute_name(self):
        for bonus in self:
            if bonus.config_id and bonus.employee_id and bonus.date:
                bonus.name = f"{bonus.config_id.name} - {bonus.employee_id.name} - {bonus.date.strftime('%B %Y')}"
            else:
                bonus.name = "Bono"

    #NOTE: used when creating bonus manually
    @api.onchange('config_id')
    def _onchange_config_id(self):
        amount = self.config_id._get_amount(self.employee_id) if self.config_id else False
        self.amount = amount if amount else 0.0
            
    def action_cancel(self):
        # Aquí iría la lógica para revertir si ya fue pagado, si es necesario.
        self.write({'state': 'cancel'})
