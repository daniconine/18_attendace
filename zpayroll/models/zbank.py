from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from odoo.modules.module import get_module_root


#Modulo de cuents bancacrias para empelados 

class ZEmployeeBankInfo(models.Model):
    _name = 'zemployee.bank.info'
    _description = 'Información bancaria del empleado'

    name = fields.Char(string='Referencia', compute='_compute_name', store=True)
    employee_extension_id = fields.Many2one(
        'zemployee.extension',
        string='Ficha del empleado',
        required=True,
        ondelete='cascade')
    
    company_id = fields.Many2one(
    'res.company',
    string='Compañía',
    related='employee_extension_id.company_id',
    store=True,
    readonly=True,
    index=True)

    account_type = fields.Selection([
        ('salary', 'Cuenta Sueldo'),
        ('cts', 'Cuenta CTS'),
        ('eps', 'Cuenta EPS'),
        ('other', 'Cuenta Otros'),        
    ], string='Tipo de cuenta',)

    bank_id = fields.Many2one('res.bank', string='Banco')
    account_number = fields.Char(string='Número de cuenta')
    cci = fields.Char(string='CCI')
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id)

    _sql_constraints = [(
        'unique_account_type_per_extension',
        'unique(employee_extension_id, account_type)',
        'Ya existe una cuenta de este tipo para esta ficha del empleado.' )]
    
    @api.depends('account_type', 'bank_id', 'employee_extension_id')
    def _compute_name(self):
        selection_dict = dict(self._fields['account_type'].selection)
        for rec in self:
            tipo = selection_dict.get(rec.account_type, '')
            nombre = rec.employee_extension_id.employee_id.name or ''
            rec.name = f"{tipo} - {nombre}" if nombre else tipo