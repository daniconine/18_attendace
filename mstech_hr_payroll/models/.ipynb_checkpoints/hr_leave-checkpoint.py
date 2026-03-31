# -*- coding: utf-8 -*-

#from datetime import datetime, timedelta, time
#from pytz import timezone

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    early_vacation = fields.Boolean(string="Vacaciones a cuenta")
