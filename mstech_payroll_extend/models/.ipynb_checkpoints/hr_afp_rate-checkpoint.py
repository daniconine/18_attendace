# mstech_payroll_extend/models/hr_afp_rate.py

from odoo import models, fields


class HrAfpRate(models.Model):
    _name = 'hr.afp.rate'
    _description = 'Tasas Mensuales de AFP'
    _order = 'date_from desc'

    afp_id = fields.Many2one('hr.afp', string="AFP", required=True, ondelete='cascade')
    date_from = fields.Date(string="Vigente Desde", required=True)
    
    # El aporte obligatorio es fijo (10%), pero lo ponemos como parámetro por si cambia por ley.
    mandatory_contribution_rate = fields.Float(
        string="Tasa Aporte Obligatorio (%)", 
        default=10.0, 
        digits='Payroll Rate'
    )
    
    insurance_premium_rate = fields.Float(
        string="Tasa Prima de Seguro (%)", 
        required=True, 
        digits='Payroll Rate'
    )
    
    commission_rate = fields.Float(
        string="Tasa Comisión sobre Flujo (%)", 
        required=True, 
        digits='Payroll Rate'
    )


class HrAfp(models.Model) :
    _name = 'hr.afp'
    _description = 'AFP'
    
    name = fields.Char(string='AFP', required=True)
    rate_ids = fields.One2many(string="Tasas mensuales", comodel_name="hr.afp.rate", inverse_name="afp_id")

    def get_rate_values(self, date):
        """
        Busca el valor de un la tasa más reciente o la correspondiente a una fecha
        """
        self.ensure_one()
        rate = self.env['hr.afp.rate'].search([
            ('afp_id', '=', self.id),
            ('date_from', '<=', date)
        ], limit=1, order='date_from DESC')
        return rate
