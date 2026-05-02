from odoo import models, fields, api
from odoo.exceptions import UserError


class ZPayrollClosing(models.Model):
    _name = 'zpayroll.closing'
    _description = 'Cierre de Planilla'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, employee_id'

    name = fields.Char(string='Nombre', required=True, copy=False, tracking=True)

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Nómina',
        required=True,
        copy=False,
        tracking=True,
        ondelete='restrict'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',      
        tracking=True
    )
   

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )

    date_from = fields.Date(string='Desde', required=True, tracking=True)
    date_to = fields.Date(string='Hasta', required=True, tracking=True)
    payroll_month=fields.Char(string='MES',)
    vacation=fields.Char(string='Vacaciones',)
    leave=fields.Char(string='Ausencias',)
    
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('calculated', 'Calculado'),
        ('accounted', 'Contabilizado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True)

    # Parámetros usados
    payroll_uit = fields.Float(string='UIT usada', readonly=True)
    payroll_rmv = fields.Float(string='RMV usada', readonly=True)
    payroll_onp_rate = fields.Float(string='% ONP usado', readonly=True)
    payroll_essalud_rate = fields.Float(string='% EsSalud usado', readonly=True)

    # Resumen remunerativo
    basic_amount = fields.Float(string='Básico')
    overtime_amount = fields.Float(string='Horas Extras (HE)')
    rc_overtime= fields.Float(string='HE Remuneracion Computable')
    comision_amount= fields.Float(string='Comisiones (COM)')
    rc_comision= fields.Float(string='COM Remuneracion Computable')
    bono_amount= fields.Float(string='Bonificaciones (BONO)')
    bono_amount= fields.Float(string='BONO Remuneracion Computable')
    
    gross_amount = fields.Float(string='Remuneración bruta')

    # Descuentos y aportes
    onp_amount = fields.Float(string='ONP', readonly=True)
    afp_amount = fields.Float(string='AFP', readonly=True)
    fifth_income_tax_amount = fields.Float(string='Renta 5ta', readonly=True)
    essalud_amount = fields.Float(string='EsSalud', readonly=True)

    # Resultado
    
    total_deductions = fields.Float(string='Total descuentos', readonly=True)
    net_amount = fields.Float(string='Neto a pagar', readonly=True)
    company_cost_amount = fields.Float(string='Costo empresa', readonly=True)



    _sql_constraints = [
        (
            'unique_payslip_closing',
            'unique(payslip_id)',
            'Ya existe un cierre de planilla para esta nómina.'
        )
    ]

    @api.model
    def create_from_payslip(self, payslip):
        if not payslip:
            raise UserError('No se ha seleccionado una nómina.')

        existing = self.search([('payslip_id', '=', payslip.id)], limit=1)
        if existing:
            return existing

        return self.create({
            'name': 'Cierre - %s' % (payslip.name or payslip.employee_id.name),
            'payslip_id': payslip.id,
            'employee_id': payslip.employee_id.id,
            'company_id': payslip.company_id.id,
            'date_from': payslip.date_from,
            'date_to': payslip.date_to,
        })

   

    def action_validate(self):
        self.write({'state': 'accounted'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})