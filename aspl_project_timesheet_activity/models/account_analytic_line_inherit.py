# models/account_analytic_line_inherit.py
from odoo import fields, models

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    # Período 24→25
    x_period_id = fields.Many2one(
        "timesheet.period", string="Período Hoja Tiempo"
    )
    x_periodo_hextras_id = fields.Many2one(
        "timesheet.period.hextras", string="Período Horas Extras"
    )
    x_periodo_comisiones_id = fields.Many2one(
        "timesheet.period.comisiones", string="Período Comisiones"
    )
    x_periodo_dictado_id = fields.Many2one(
        "timesheet.period.dictado", string="Período Dictado de Clases"
    )
    x_periodo_bono_id = fields.Many2one(
        "timesheet.period.bono", string="Período Bono/ Bonificación"
    )
    
    
    
    
    # 91/94/95 (rápido para demo). Si prefieres, cambia a Many2one 'account.account'
    x_account_kind = fields.Selection([
        ("91", "91 - Costo / Producción"),
        ("94", "94 - Administrativo"),
        ("95", "95 - Costo de Venta"),
    ], string="Cuenta Contable (tipo)")
    # % de asignación (captura manual)
    x_percent = fields.Float(string="Asignación (%)")
    linea_negocio = fields.Selection([
        ("maestria", "Maestría en Gestión Minera"),
        ("capacitacion", "Capacitación Continua"),
        ],string="Linea de Negocio")
    fech_devengo = fields.Date(string="Fecha Inicio Devengo")
    # Nuevo campo: Selección del recargo de horas extras
    overtime_rate = fields.Selection([
        ('0', 'Sin recargo'),
        ('15', '15% Recargo (Por Ley)'),
        ('35', '35% Recargo (Por Ley)'),
        ('100', '100% Recargo (Por Ley)'),
    ], string="Recargo H Extra", default='0', required=True)
    