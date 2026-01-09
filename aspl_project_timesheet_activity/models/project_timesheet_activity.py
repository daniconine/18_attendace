# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ProjectTimesheetActivity(models.Model):
    _name = "project.timesheet.activity"
    _description = "Project Timesheet Activity"

    name = fields.Char("Activity")


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    timesheet_activity_id = fields.Many2one('project.timesheet.activity', "Activity")
