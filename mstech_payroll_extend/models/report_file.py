# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class HrReportFile(models.Model):
    _name = 'hr.report.file'
    _description = 'Archivo de Reporte de Nómina Generado'

    name = fields.Char(string="Nombre de Archivo", required=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', string="Lote de Nóminas de Origen")
    
    file_data = fields.Binary(string="Archivo")
    file_name = fields.Char(string="Nombre del Archivo Descargable")
    
    generation_date = fields.Datetime(string="Fecha de Generación", default=fields.Datetime.now)
    generated_by_id = fields.Many2one('res.users', string="Generado por", default=lambda self: self.env.user)

    def action_download_file(self):
        file_name = self.file_name
        action = {
            'type': 'ir.actions.act_url',
            'name': file_name,
            'url': '/web/content/%(model)s/%(id)s/file_data/%(filename)s?download=true' % {
                'model': 'hr.report.file',
                'id': self.id,
                'filename': file_name,
            },
        }
        return action
