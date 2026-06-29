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
            "security/ir.model.access.csv",
            'security/record_rules.xml',
            
            
            #"views/zperiod_batch_views.xml",
            "views/zperiod_views.xml",
            #"views/menus.xml",
            'views/zemployee_extension_views.xml',
            'views/hr_labor_regime_pe_views.xml',
            'views/hr_afp_views.xml',
            'views/hr_afp_rate_views.xml',
            'views/employee_family_views.xml',
            'views/zemployee_bank_info_views.xml',
            'views/hr_contract_views.xml',
            #'views/zemployee_views.xml',
            'views/hr_payslip_views.xml',
            'views/hr_salary_rule_views.xml',
            'views/zpayroll_closing_views.xml',
            'views/hr_employee_views.xml',
            
            'data/hr_afp_data.xml',
            'data/hr_afp_rate_data.xml',
            'data/hr_labor_regime_data.xml',
            'data/hr_salary_rule_category_pe.xml',
            'data/hr_salary_rule_pe.xml',
            'data/paperformat.xml',
            
            'wizard/zpayroll_report_nomina_views.xml',
            'report/report_boleta_pago.xml',
            'report/hr_payslip_menu.xml',
            
            
            'views/zemployee_menu.xml',
            ],
    'assets': {
        'web.assets_backend': [
            "zpayroll/static/src/css/boleta_pago.css",
        ],
    },
    
}
