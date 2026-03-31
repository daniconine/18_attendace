# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils

from datetime import date, datetime, time
import logging

_logger = logging.getLogger(__name__)

# This will generate 16th of days
ROUNDING_FACTOR = 16


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    #@override
    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        Returns create vals for 'hr.payslip.worked.days'
        """
        res = []
        for contract in contracts.filtered(lambda c: c.resource_calendar_id):  #if schedule is defined
            date_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            date_to = datetime.combine(fields.Date.from_string(date_to), time.max)
            hours_per_day = contract.resource_calendar_id.hours_per_day

            work_entries = self.env['hr.work.entry'].with_context(lang="es_PE")._read_group(
                [
                    ('state', 'in', ['validated', 'draft']),
                    ('contract_id', '=', contract.id),
                    ('date_start', '>=', date_from),
                    ('date_stop', '<=', date_to)
                ],
                ['work_entry_type_id'],
                ['duration:sum'])
            
            for entry, hours in work_entries:
                vals = {
                    'name': entry.name,
                    #'sequence': ,  #skipped
                    'code': entry.code or 'NO_CODE',
                    'number_of_days': float_utils.round(ROUNDING_FACTOR * hours / hours_per_day) / ROUNDING_FACTOR,
                    'number_of_hours': hours,
                    'contract_id': contract.id,
                }
                res.append(vals)
        return res
                
