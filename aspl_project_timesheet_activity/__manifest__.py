# -*- coding: utf-8 -*-
###############################################################################
#
# Aspire Softserv Pvt. Ltd.
# Copyright (C) Aspire Softserv Pvt. Ltd.(<https://aspiresoftserv.com>).
#
###############################################################################
{
    "name": "Project Timesheet Activity",
    "category": "Timesheet",
    "summary": "Categorize your work entries by its type.",
    "version": "18.0.0.1.0",
    "license": "AGPL-3",
    'description': """
        This module adds a new field 'Activity' in timesheet line. User can analyze the time spent in different type of activities. This analysis helps in better planning.
    """,
    "author": "Aspire Softserv Pvt. Ltd",
    "website": "https://aspiresoftserv.com",
    "depends": ['hr_timesheet', 'project'],
    "data": [
        "security/ir.model.access.csv",
        "views/project_timesheet_activity_configuration.xml",
        "views/inherit_project_task.xml",
        "views/timesheet_period_views.xml",
        "views/timesheet_period_hextras_views.xml",
        "views/timesheet_period_comisiones_views.xml",
        "views/timesheet_period_dictado_views.xml",
        "views/timesheet_period_bono_views.xml"
        
    ],
    "application": True,
    "installable": True,
    "maintainer": "Aspire Softserv Pvt. Ltd",
    "support": "odoo@aspiresoftserv.com",
    "images": ['static/description/banner.gif'],
}
