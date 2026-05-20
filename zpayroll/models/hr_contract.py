# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class HrContract(models.Model):
    _inherit = 'hr.contract'

    code = fields.Char(string='Código Contrato', help="Código interno del contrato", tracking=True)
    
    hours_per_day = fields.Float(string="Horas de trabajo promedio al día", digits=(16, 2), 
                                 tracking=True, store =True)

    hours_per_month = fields.Float(string="Horas PLAME reportado al mes",compute="_compute_working_hours",
                                   store=True,digits=(16, 2),)

    hours_per_week = fields.Float(string="Horas de trabajo a la semana",digits=(16, 2),)

    cost_per_hour_month = fields.Monetary(string="Costo por hora mensual",compute="_compute_working_hours",
                            store=True,digits=(16, 2),)

    @api.depends('hours_per_day', 'wage')
    def _compute_working_hours(self):
        for contract in self:
            contract.hours_per_month = contract.hours_per_day * 30

            if contract.hours_per_month:
                contract.cost_per_hour_month = contract.wage / contract.hours_per_month
            else:
                contract.cost_per_hour_month = 0.0
    
