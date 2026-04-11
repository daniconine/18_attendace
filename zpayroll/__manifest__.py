# -*- coding: utf-8 -*-
{
    "name": "ZPayroll",
    "summary": "Módulo de Integración de Nomina GERENS",
    "description": """
        Integración y Personlización con hr_payroll (Community):
        - Integración de Zperiod con nómina
        - PErsonalización de Nominma
        - Utlimo modulo de RRHH
    """,
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Gerens",
    "license": "AGPL-3",
    "application": True,          # <- IMPORTANTE para Apps
    "installable": True,
    "depends": ["base", "base_rrhh", "mail", "hr","zattendance","zleave","zperiod",
                "hr_attendance",'hr_work_entry',"analytic","hr_payroll_community",
                ],
    "data": [
            #"security/ir.model.access.csv",
            #"views/zperiod_batch_views.xml",
            "views/zperiod_views.xml",
            #"views/menus.xml",
            ],
    'assets': {
        'web.assets_backend': [
        ],
    },
    
}
