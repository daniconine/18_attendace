# mstech_payroll_extend/models/hr_afp_rate.py

from odoo import models, fields


class HrJobOccupation(models.Model):
    _name = 'hr.job.occupation'
    _description = 'Ocupación'

    name = fields.Char(string="Descripción")
    code = fields.Char(string="Código", size=6)
