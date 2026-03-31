from odoo import models, fields


class PeEconomicActivity(models.Model):
    _name = 'pe.economic.activity'
    _description = 'Actividad Económica SUNAT'

    code = fields.Char(string='Código SUNAT', required=True)
    name = fields.Char(string='Descripción', required=True)
    active = fields.Boolean(default=True)
