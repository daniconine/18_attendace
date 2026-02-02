# -*- coding: utf-8 -*-
{
    "name": "ZLeave",
    "summary": "Licencia/Permisos/Vacaciones GERENS",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Gerens",
    "license": "AGPL-3",
    "application": True,          # <- IMPORTANTE para Apps
    "installable": True,
    "depends": ["base", "mail", "hr","zattendance", "hr_attendance",'hr_work_entry'],
    "data": [
        "security/groups.xml", 
        "security/record_rules.xml",
        
        "security/ir.model.access.csv",
        
        'views/email_template.xml',
        #"views/zattendance_day_views.xml",
        #"views/hr_attendance_views.xml",
        #"views/ir_cron_jobs.xml", 
        #"views/r_calendar_attendance_views.xml",
        #'views/hr_work_entry_views.xml',
        'views/permission_views.xml',
        'views/zvacation_views.xml',
        'views/zvacation_year_views.xml',  
        'views/zvacation_allocate_views.xml',     
        
        
        "views/zleave_menus.xml",
        
    ],
    'assets': {
        'web.assets_backend': [
            'zleave/static/src/css/styles.css',  # Asegúrate de agregar tu archivo CSS aquí
        ],
    },
    
}
