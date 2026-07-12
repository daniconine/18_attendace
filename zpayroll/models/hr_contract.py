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
    
    
    #Para logica de retencion de 5ta Categoria
    r5_other_job = fields.Boolean(string='Tiene otro trabajo para Renta 5ta',default=False,
            help='Marcar si el trabajador tiene otro trabajo y se debe considerar esa remuneración para la proyección de renta de quinta.')

    r5_other_job_wage = fields.Float(string='Remuneración mensual del otro trabajo',default=0.0,
            help='Remuneración mensual percibida en otro trabajo, usada para proyectar renta de quinta.')
    

    #### Remuneracion Computable Mensual
    bono_fijo_computable_mensual = fields.Monetary(
        string="Bono fijo computable mensual",
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help="Monto fijo mensual que forma parte de la remuneración computable."
    )

    concepto_fijo_computable_mensual = fields.Monetary(
        string="Concepto fijo computable mensual",
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help="Otro monto fijo mensual que forma parte de la remuneración computable."
    )