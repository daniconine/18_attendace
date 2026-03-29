# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ZPeriodBatch(models.Model):
    _name = "zperiod.batch"
    _description = "Generador en Lote de Períodos"
    _inherit = ["mail.thread"]
    _order = "date_start desc"
    
    name = fields.Char(string="Nombre del Lote", required=True)
    date_start = fields.Date(string="Fecha Inicio", required=True)
    date_end = fields.Date(string="Fecha Fin", required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    