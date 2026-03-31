from odoo import models, fields, api
from odoo.exceptions import UserError

class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    receives_gratification = fields.Boolean(string="Recibe gratificaciones", default=True)
    plame_code = fields.Char(string='Código en PLAME')
