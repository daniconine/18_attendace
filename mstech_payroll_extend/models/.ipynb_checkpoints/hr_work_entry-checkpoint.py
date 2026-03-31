# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'
    
    overtime_request_id = fields.Many2one(comodel_name='hr.overtime.request', string='Solicitud de Horas Extra')
    
    def write(self, vals):
        if ('active' in vals) and (not vals.get('active')):
            overtime_request_ids = self.mapped('overtime_request_id').filtered(lambda l: l.approved_work_entry_id and (l.state == 'approved'))
            if overtime_request_ids:
                overtime_request_ids.write({'approved_work_entry_id': False})
                overtime_request_ids.action_reset_to_draft()
                overtime_request_ids.action_approve()
        
        return super().write(vals)
