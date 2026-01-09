from odoo import models, fields, api
from datetime import datetime


class ZAttendanceDay(models.Model):
    _inherit = "zattendance.day" 
    
    
    
    permiso_request_id = fields.Many2one( "zattendance.permission",
                        string="Solicitud de Permiso",tracking=True, index=True, )
