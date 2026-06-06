from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


#Hoja de tiempos
class ZPeriodSegmentLine(models.Model):
    _name = "zperiod.segment.line"
    _description = "Línea de Segmentación"

    #relacion con zpeiod
    period_id = fields.Many2one("zperiod", string="Periodo", required=True, ondelete="cascade")
    month = fields.Selection(related="period_id.month",string="Mes",store=True,readonly=True,)
    year = fields.Integer(related="period_id.year",string="Año",store=True,readonly=True,)
    employee_id = fields.Many2one(related="period_id.employee_id",string="Empleado",store=True,readonly=True,)
    
    
    percentage = fields.Float(string="% Dedicado", required=True)
    note = fields.Char(string="Descripción de la Actividad Realizada")
    
    plan_id = fields.Many2one("account.analytic.plan", string = "Linea de Negocio")
    analytic_account_id = fields.Many2one("account.analytic.account",
                            string="Cuenta Analítica Administitiva",
                            domain="[('plan_id', '=', plan_id)]",
                            required=True)
        
    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        for rec in self:
            if rec.analytic_account_id and rec.analytic_account_id.plan_id != rec.plan_id:
                rec.analytic_account_id = False

    @api.constrains("plan_id", "analytic_account_id")
    def _check_analytic_account_plan(self):
        for rec in self:
            if rec.plan_id and rec.analytic_account_id:
                if rec.analytic_account_id.plan_id != rec.plan_id:
                    raise ValidationError(
                        "La cuenta analítica no pertenece al plan seleccionado."
                    )

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
