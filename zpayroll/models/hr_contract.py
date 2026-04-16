# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class HrContract(models.Model):
    _inherit = 'hr.contract'

    hours_per_day = fields.Float(
        string="Horas de trabajo promedio al día",
        digits=(16, 2),)