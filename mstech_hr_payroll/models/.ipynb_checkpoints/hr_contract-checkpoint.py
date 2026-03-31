# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class EmploymentRegime(models.Model) :
    _name = 'employment.regime'
    _description = 'Régimen Laboral'
    
    name = fields.Char(string='Régimen Laboral', required=True)

    
class PensionSystem(models.Model) :
    _name = 'pension.system'
    _description = 'Régimen Laboral'
    
    name = fields.Char(string='Régimen Pensionario', required=True)

    
class HealthCareSystem(models.Model) :
    _name = 'health.care.system'
    _description = 'Régimen Laboral'
    
    name = fields.Char(string='Régimen de Salud', required=True)


class SCTRTable(models.Model) :
    _name = 'sctr.table'
    _description = 'Tabla SCTR'
    
    name = fields.Char(string='Tabla SCTR', required=True)


class HrContract(models.Model):
    _inherit = 'hr.contract'

    #GENERAL
    employment_regime_id = fields.Many2one(string="Régimen Laboral", comodel_name="employment.regime", tracking=True)
    pension_system_id = fields.Many2one(string="Régimen Pensionario", comodel_name="pension.system", tracking=True)
    health_care_system_id = fields.Many2one(string="Régimen de Salud", comodel_name="health.care.system", tracking=True)
    afp_comission_type = fields.Selection(string="Tipo de comisión AFP", selection=[('on_flow', 'Sobre el flujo'), ('annual_balance', 'Anual sobre saldo')], tracking=True)

    #OTROS CONCEPTOS
    main_feed_money = fields.Monetary(string='Alimentación principal en dinero', tracking=True)
    productivity_bonus = fields.Monetary(string='Bono de productividad', tracking=True)
    eps_cost = fields.Monetary(string='Costo de EPS', tracking=True)
    mobility = fields.Monetary(string='Movilidad de libre disposición', tracking=True)
    sctr_table_id = fields.Many2one(string='Tabla SCTR', comodel_name="sctr.table", tracking=True)

    #DESCUENTOS
    discount_type = fields.Selection(string='Tipo de retención judicial', selection=[('fixed', 'Fijo')], tracking=True)  #TODO: fill
    discount = fields.Monetary(string='Descuento judicial', tracking=True)

    #CÁLCULO DE LA RENTA DE 5TA
    receives_commission = fields.Boolean(string="Percibe comisiones", tracking=True)
    estimated_monthly_bonus = fields.Monetary(string="Bonificaciones regulares mensuales estimadas", tracking=True)
    estimated_monthly_commission = fields.Monetary(string="Comisiones o destajo mensuales estimadas", tracking=True)
    past_compensation = fields.Monetary(string="Total de remuneraciones anteriores del periodo", tracking=True)
