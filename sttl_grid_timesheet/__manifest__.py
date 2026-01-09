# -*- coding: utf-8 -*-
{
    'name': "Timesheet Grid View",
    'summary': "Basic 2D Grid view for odoo",
    'description': """
The Timesheet Grid View offers a clear and structured layout to log and track time entries by project, task, and date. 
It supports both manual entry and timer-based logging for convenience.
    """,

    'author': "Silver Touch Technologies Limited",
    'website': "https://www.silvertouch.com/",

    'version': '0.1',
    'depends': ['hr_timesheet'],
    'data': [
        'views/timesheet_grid.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sttl_grid_timesheet/static/src/js/**',
            'sttl_grid_timesheet/static/src/xml/**',
        ],
    },
    'images': ['static/description/banner.png'],
}
