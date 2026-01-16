# -*- coding: utf-8 -*-
{
    "name": "ZAttendance",
    "summary": "Asistencia GERENS diaria consolidada (planificado vs real)",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Gerens",
    "license": "AGPL-3",
    "application": True,          # <- IMPORTANTE para Apps
    "installable": True,
    "depends": ["base", "mail", "hr", "hr_attendance",'hr_work_entry'],
    "data": [
        "security/groups.xml",
        "security/record_rules.xml",
         
        "security/ir.model.access.csv",
        
        "views/zattendance_day_views.xml",
        "views/hr_attendance_views.xml",
        "views/ir_cron_jobs.xml",
        "views/ir_cron_recalcular.xml",  
        "views/r_calendar_attendance_views.xml",
        'views/hr_work_entry_views.xml',
         
        
        
        "views/zattendance_menus.xml",
        
    ],
}
