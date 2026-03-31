# -*- coding: utf-8 -*-

{
    'name': 'Mstech - HR Payroll Community',
    'version': '1.0.0',
    'author': 'Meditech',
    'category': 'Technical',
    'summary': 'Módulo de personalización de módulos de Recursos Humanos.',
    'license': 'Other proprietary',
    'depends' : [
        'hr_payroll_community',  #'hr_payroll_attendance', #->hr_payroll (enterprise)
    ],
    'data': [
        'security/ir.model.access.csv',

        
        'views/hr_contract_views.xml',
        'views/employee_relative_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'sequence': 1,
}
