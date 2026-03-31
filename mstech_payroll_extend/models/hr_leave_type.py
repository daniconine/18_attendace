from odoo import models, fields, api
from odoo.exceptions import UserError

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    #requires_attachment = fields.Boolean(string="Requiere justificación")
    #NOTE: field replaced with support_document

    plame_suspension_type_id = fields.Many2one(
        'hr.plame.suspension.type',
        string="Tipo de Suspensión (PLAME)",
        help="Código oficial de SUNAT para este tipo de ausencia, usado en la declaración del PLAME."
    )
