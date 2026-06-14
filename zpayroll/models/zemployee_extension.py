from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from odoo.modules.module import get_module_root
  

class ZEmployeeExtension(models.Model):
    _name = 'zemployee.extension'
    _description = 'Extensión del Empleado para normativa peruana'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(comodel_name='hr.employee',string='Empleado', required=True,
                                 ondelete='cascade', tracking=True)
    
    company_id = fields.Many2one(comodel_name='res.company',
                    string='Compañía',related='employee_id.company_id',
                    store=True, readonly=True,index=True)

    entry_date = fields.Date(string='Fecha de Ingreso',tracking=True)
    termination_date = fields.Date(string='Fecha de Cese',tracking=True,)
    cuspp = fields.Char(string='CUSPP (PE)')    
    is_disabled_person = fields.Boolean(string="Tiene alguna discapacidad")
    is_family_mother = fields.Selection(string="Madre con responsabilidad familiar",
                        selection=[('none', 'No aplica'), ('1', 'Sí'), ('0', 'No')])
    study_school_type = fields.Selection(string="Tipo de Centro de Formación Profesional",
                         selection=[('1', 'Centro Educativo'), ('2', 'Universidad'),('3', 'Instituto'), ('4', 'Otros') ])
    pensioner_type = fields.Selection(string="Pensionista",selection=[
                    ('24', 'PENSIONISTA O CESANTE'), ('26', 'PENSIONISTA - LEY 28320')])
    
    #otrasrelaciones con tablas
    family_ids = fields.One2many( comodel_name='employee.family',inverse_name='zemployee_extension_id',string='Familiares')
    pe_labor_regime_id = fields.Many2one('hr.labor.regime.pe', string="Régimen Laboral", tracking=True)

    pe_pension_scheme = fields.Selection([('onp', 'ONP'),('spp', 'SPP'),], 
                                         string="Régimen Pensionario", tracking=True)

    afp_id = fields.Many2one('hr.afp', string='AFP (si aplica)', tracking=True)

    afp_commission_type = fields.Selection([('flow', 'Sobre el flujo'),
                                            ('mixed', 'Mixta'),
                                            ('mixed2', 'Mixta 2.0'),
                                        ], string='Tipo de comisión AFP', tracking=True)

    pe_health_scheme = fields.Selection([('essalud_regular', 'ESSALUD REGULAR'),
                                            ('eps', 'EPS'),
                                            ('essalud_sctr', 'SCTR ESSALUD'),
                                            ('eps_sctr', 'SCTR EPS'),
                                            ('sis', 'SIS'),
                                        ], string='Régimen de salud', tracking=True)
    
    currency_id = fields.Many2one('res.currency',string='Moneda',
                        default=lambda self: self.env.company.currency_id.id)
    cuentas_bancarias_ids = fields.One2many('zemployee.bank.info',       # Modelo destino
                                'employee_extension_id',string='Cuentas Bancarias')
    
    
    
    eps_cost = fields.Monetary(string='Costo EPS',currency_field='currency_id')
    judicial_deduction_type = fields.Selection([('fixed', 'Fijo'),('percent', 'Porcentaje'),], string='Tipo de retención judicial')
    judicial_deduction_amount = fields.Monetary( string='Descuento judicial', currency_field='currency_id')
    
    sctr_table = fields.Selection([('sctr_public', 'SCTR Público'),
                                    ('sctr_private_percentage', 'SCTR Privado Porcentaje'),
                                    ('sctr_private_flat', 'SCTR Privado Monto fijo'),], string='Tabla SCTR')
    
    
    
    cuenta_sueldo = fields.Many2one( 'zemployee.bank.info',string='Cuenta Sueldo',ondelete='set null')

    cuenta_cts = fields.Many2one('zemployee.bank.info',string='Cuenta CTS',ondelete='set null')

    cuenta_eps = fields.Many2one('zemployee.bank.info',string='Cuenta EPS',ondelete='set null')

    _sql_constraints = [
        ('employee_id_unique', 'unique(employee_id)', 'Ya existe una extensión para este empleado.')]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        bank_model = self.env['zemployee.bank.info']

        for record in records:
            cuenta_sueldo = bank_model.create({
                'employee_extension_id': record.id,
                'account_type': 'salary',
                'currency_id': record.currency_id.id,
            })

            cuenta_cts = bank_model.create({
                'employee_extension_id': record.id,
                'account_type': 'cts',
                'currency_id': record.currency_id.id,
            })

            cuenta_eps = bank_model.create({
                'employee_extension_id': record.id,
                'account_type': 'eps',
                'currency_id': record.currency_id.id,
            })

            record.write({
                'cuenta_sueldo': cuenta_sueldo.id,
                'cuenta_cts': cuenta_cts.id,
                'cuenta_eps': cuenta_eps.id,
            })

        return records
    