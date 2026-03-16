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
    "depends": ["base", "base_rrhh", "mail", "hr","zattendance",
                "hr_attendance",'hr_work_entry',"analytic",],
    "data": [
        "security/groups.xml",# 1. Grupos (Cimientos)
        
        # 2. Vistas y Acciones (Componentes)
        # Aquí es donde se define 'action_zleave_permission_my'
        'views/permission_views.xml',     
        'views/zvacation_views.xml',
        'views/zvacation_year_views.xml',  
        'views/zvacation_allocate_views.xml',
        'views/zovertime_views.xml',
        
        # 3. Dashboard (Depende de las acciones de arriba)
        'views/zleave_dashboard.xml',     
        
        # 4. Reglas de Seguridad (Dependen de los grupos y del dashboard)
        "security/record_rules.xml",      
        
        # 5. Resto de configuraciones
        "security/ir.model.access.csv",
        'views/email_template.xml',
        'views/dashboard_views.xml',
        'views/ir_cron_update_vacation.xml',
        "views/zleave_menus.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'zleave/static/src/css/styles.css',  # Asegúrate de agregar tu archivo CSS aquí
        ],
    },
    
}
