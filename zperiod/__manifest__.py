# -*- coding: utf-8 -*-
{
    "name": "ZPeriod",
    "summary": "Módulo de Transición y Resumen de Nómina - GERENS",
    "description": """
        Gestión de periodos previos a la generación de planilla:
        - Validación de incidencias.
        - Resumen de asistencia y permisos.
        - Consolidación de novedades.
    """,
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Gerens",
    "license": "AGPL-3",
    "application": True,          # <- IMPORTANTE para Apps
    "installable": True,
    "depends": ["base", "base_rrhh", "mail", "hr","zattendance",
                "hr_attendance",'hr_work_entry',"analytic","zleave","hr_payroll_community",],
    "data": [
            "security/ir.model.access.csv",
            "security/record_rule.xml",
            
            "views/zperiod_batch_views.xml",
            "views/zperiod_views.xml",
            "views/segment_line_views.xml",
            
            "views/cron_zperiod_actualizar.xml",
            "views/menus.xml",
            ],
    'assets': {
        'web.assets_backend': [
        ],
    },
    
}
