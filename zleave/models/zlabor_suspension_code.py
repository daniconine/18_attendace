# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


### Adicional para complementar a las solicitudes laborables 
class ZLaborSuspensionCode(models.Model):
    _name = "zlabor.suspension.code"
    _description = "Códigos de Suspensión Laboral PLAME"

    name = fields.Char(string="Nombre Cotidiano de Suspensión Laboral", required=True)
    code = fields.Char(string="Código PLAME", required=True,help="Código oficial según Tabla 21 de SUNAT")
    description = fields.Char(string="Descripción o Nombre en PLAME", required=True)  # Ej: 'S.P. FALTAS INJUSTIFICADAS'
    type_suspension = fields.Selection([('perfecta','Suspensión Perfecta'), 
                                        ('imperfecta','Suspensión Imperfecta'),
                                        ('subsidio', 'Licencia Subsidiada'),],
                                        string="Tipo de suspensión", required=True)
    asumido_por = fields.Selection([('empleador','Empleador'), ('essalud','EsSalud'), ('ninguno','Ninguno')],
                                   string="Quién asume el costo", default='ninguno')
    
    visible_in_permission = fields.Boolean(string="Visible en Solicitudes",
                        default=True,help="Si está en False, este código no se mostrará en ZleavePermission")
    
    _sql_constraints = [('unique_code', 'unique(code)', 'El código PLAME ya existe en el sistema.'),
                    ('unique_name', 'unique(name)', 'El nombre cotidiano ya existe en el sistema.')]
    
    