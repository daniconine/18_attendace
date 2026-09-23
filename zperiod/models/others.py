from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError



class ZPeriodClassLine(models.Model):
    _name = "zperiod.class.line"
    _description = "Dictado de Clases"

    period_id = fields.Many2one("zperiod", string="Periodo", required=True, ondelete="cascade")
    month = fields.Selection(related="period_id.month",string="Mes",store=True,readonly=True,)
    year = fields.Integer(related="period_id.year",string="Año",store=True,readonly=True,)
    employee_id = fields.Many2one(related="period_id.employee_id",string="Empleado",store=True,readonly=True,)
    
           
    date = fields.Date(string="Fecha", required=True)
    course_name = fields.Char(string="Curso", required=True)
    hours = fields.Float(string="Horas")
    amount = fields.Monetary(string="Monto S/", required=True)
    currency_id = fields.Many2one('res.currency', string="Moneda", default=lambda self: self.env.company.currency_id)

    note = fields.Char(string="Observaciones")
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cuenta Analitica (CCA)")

class ZBonus(models.Model):
    _name = 'z.bonus'
    _description = 'Bono de Empleado'
    _order = 'date desc'
    
    #relacion con zperiod
    period_id = fields.Many2one("zperiod", string="Periodo", ondelete="cascade")
    month = fields.Selection(related="period_id.month",string="Mes",store=True,readonly=True,)
    year = fields.Integer(related="period_id.year",string="Año",store=True,readonly=True,)
    employee_id = fields.Many2one(related="period_id.employee_id",string="Empleado",store=True,readonly=True,)
    
    date = fields.Date(string="Fecha", default=fields.Date.context_today)
    amount = fields.Monetary(string="Monto Bono", required=True)   
    currency_id = fields.Many2one('res.currency', string="Moneda", default=lambda self: self.env.company.currency_id)
    
    note = fields.Char(string="Descripción del Bono Asignada al Empleado(a)")
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cuenta Analitica (CCA)")  
   


class ZCommission(models.Model):
    _name = 'z.commission'
    _description = 'Comisión Generada'
    _order = 'date desc'
    
    period_id = fields.Many2one("zperiod", string="Periodo", ondelete="cascade")
    month = fields.Selection(related="period_id.month",string="Mes",store=True,readonly=True,)
    year = fields.Integer(related="period_id.year",string="Año",store=True,readonly=True,)
    employee_id = fields.Many2one(related="period_id.employee_id",string="Empleado",store=True,readonly=True,)
    
   
    note = fields.Char(string="Descripción de la Comisión Asignada al Empleado(a)")
    date = fields.Date(string="Fecha Comisión", required=True)
    
    amount = fields.Monetary(string="Monto Comisión", required=True)
    currency_id = fields.Many2one('res.currency', string="Moneda", default=lambda self: self.env.company.currency_id)
    
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cuenta Analitica (CCA)")  
