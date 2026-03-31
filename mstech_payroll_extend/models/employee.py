from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from odoo.modules.module import get_module_root

import os
import logging

_logger = logging.getLogger(__name__)


class HrEmployeeDeclaracion5taPe(models.Model):
    _name = 'hr.employee.declaracion.5ta.pe'
    _description = 'Declaración Jurada de 5ta del Empleado'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    active = fields.Boolean(string='Activo', default=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Empleado', ondelete='cascade')
    company_id = fields.Many2one(comodel_name='res.company', string='Compañía', related='employee_id.company_id', store=True, readonly=False)
    fiscal_year = fields.Integer(string='Año Fiscal', tracking=True, default=lambda self: fields.Date.context_today(self).year)
    external_revenue = fields.Boolean(string='Percibe Ingresos Externos')
    external_amount = fields.Float(string='Monto de Ingresos Externos')
    retention_partner_id = fields.Many2one(comodel_name='res.partner', string='Empresa de Retención')
    signature = fields.Binary(string='Firma')
    signature_date = fields.Date(string='Fecha de Firma', tracking=True)
    declaration = fields.Binary(string='Declaración')
    declaration_filename = fields.Char(string='Nombre de la Declaración')
    state = fields.Selection(string='Estado', selection=[
        ('draft', 'Borrador'),
        ('validated', 'Validado'),
        ('replaced', 'Reemplazado'),
        ('historic', 'Histórico'),
    ], required=True, default='draft', tracking=True)
    
    def button_validate(self):
        self.ensure_one()
        action = self.get_formview_action()
        current_module = os.path.dirname(os.path.abspath(__file__))
        current_module = os.path.basename(get_module_root(current_module))
        action.update({
            'view_type': 0,
            'view_mode': 0,
            'res_id': self.id,
            'views': [(self.sudo().env.ref('.'.join([
                current_module,
                'view_hr_employee_declaracion_5ta_pe_form_signature',
            ])).sudo().id, 'form')],
            'target': 'new',
        })
        del action['view_type']
        del action['view_mode']
        return action
    
    def button_finish_sign(self):
        self.ensure_one()
        fiscal_year = self.fiscal_year
        now = fields.Datetime.now()
        self.signature_date = now
        declaracion_5ta_ids = self.sudo().employee_id.declaracion_5ta_ids
        validated_ids = declaracion_5ta_ids.filtered(lambda r: r.state == 'validated')
        if validated_ids:
            current_ids = validated_ids.filtered(lambda r: r.fiscal_year == fiscal_year)
            if current_ids:
                current_ids.write({'state': 'replaced'})
            old_ids = validated_ids.filtered(lambda r: r.fiscal_year < fiscal_year)
            if old_ids:
                old_ids.write({'state': 'historic'})
        # self.state = 'validated'
        self.state = 'validated' if self.fiscal_year >= now.year else 'historic'
        return {'type': 'ir.actions.act_window_close'}
    
    def unlink(self):
        self_states = self.mapped('state')
        if (len(set(self_states)) > 1) or ((self_states or ['draft'])[0] != 'draft'):
            raise UserError('Solo puede eliminar declaraciones en estado borrador. Archívela si es necesario.')
        return super().unlink()


class HrEmployeeFamily(models.Model):
    _name = 'hr.employee.family.pe'
    _description = 'Familiar del Empleado (PE)'
    _rec_name = 'partner_id'  #CHECK

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='cascade'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Familiar',
        required=True,
        help="Contacto relacionado al familiar"
    )

    relationship = fields.Selection([
        ('child', 'Hijo'),
        ('spouse', 'Cónyuge'),
        ('parent', 'Padre/Madre'),
        ('other', 'Otro'),
    ], string='Parentesco', required=True)

    # Asignación familiar
    is_child = fields.Boolean(string='Hijo')
    is_disabled = fields.Boolean(string='Discapacitado')
    receives_disability_pension = fields.Boolean(string='Recibe pensión por discapacidad severa')
    is_student = fields.Boolean(string='Estudiante')

    # Datos relacionados automáticamente desde el partner
    document_number = fields.Char(
        string='Número de identificación',
        related='partner_id.vat',
        store=True
    )
    #NOTE: gender does not exist in native res.partner model
    gender = fields.Selection(
        string='Género',
        selection=[('male', 'Masculino'), ('female', 'Femenino'), ('other', 'Otro')],
        store=True
    )
    birth_date = fields.Date(
        string='Fecha de nacimiento',
        store=True
    )
    age = fields.Float(string='Edad', compute='_compute_age', store=True)

    @api.depends('birth_date')
    def _compute_age(self):
        for rec in self:
            if rec.birth_date:
                today = date.today()
                delta = today - rec.birth_date
                rec.age = round(delta.days / 365.25, 2)
            else:
                rec.age = 0.0

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    cuspp = fields.Char(string='CUSPP (PE)')

    educational_situation = fields.Many2one(string="Situación educativa", comodel_name="hr.educational.situation")
    is_disabled_person = fields.Boolean(string="Tiene alguna discapacidad")
    is_family_mother = fields.Selection(string="Madre con responsabilidad familiar", selection=[('none', 'No aplica'), ('1', 'Si'), ('0', 'No')])
    study_school_type = fields.Selection(string="Tipo de Centro de Formación Profesional", selection=[
        ('1', 'Centro Educativo'),
        ('2', 'Universidad'),
        ('3', 'Instituto'),
        ('4', 'Otros')
    ])
    pensioner_type = fields.Selection(string="Pensionista", selection=[('24', 'PENSIONISTA O CESANTE'), ('26', 'PENSIONISTA - LEY 28320')])

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    declaracion_5ta_ids = fields.Many2many(
        comodel_name='hr.employee.declaracion.5ta.pe',
        compute='_compute_declaracion_5ta_data',
    )
    declaracion_5ta_id = fields.Many2one(
        comodel_name='hr.employee.declaracion.5ta.pe',
        compute='_compute_declaracion_5ta_data',
    )
    declaracion_5ta_fiscal_year = fields.Integer(compute='_compute_declaracion_5ta_data')
    declaracion_5ta_external_revenue = fields.Boolean(compute='_compute_declaracion_5ta_data')
    declaracion_5ta_external_amount = fields.Float(compute='_compute_declaracion_5ta_data')
    declaracion_5ta_retention_partner_id = fields.Many2one(comodel_name='res.partner', compute='_compute_declaracion_5ta_data')
    family_ids = fields.Many2many(
        comodel_name='hr.employee.family.pe',
        compute='_compute_family_data',
    )
    dependent_children_count = fields.Integer(
        compute='_compute_family_data',
    )
    disabled_children_count = fields.Integer(
        compute='_compute_family_data',
    )
    student_children_count = fields.Integer(
        compute='_compute_family_data',
    )

    @api.depends('employee_id')
    def _compute_family_data(self):
        for record in self:
            employee_id = record.sudo().employee_id
            record.family_ids = employee_id.family_ids
            record.dependent_children_count = employee_id.dependent_children_count
            record.disabled_children_count = employee_id.disabled_children_count
            record.student_children_count = employee_id.student_children_count

    @api.depends('employee_id')
    def _compute_declaracion_5ta_data(self):
        for record in self:
            employee_id = record.sudo().employee_id
            record.declaracion_5ta_ids = getattr(employee_id, 'declaracion_5ta_ids', False)
            record.declaracion_5ta_id = getattr(employee_id, 'declaracion_5ta_id', False)
            record.declaracion_5ta_fiscal_year = getattr(employee_id, 'declaracion_5ta_fiscal_year', 0)
            record.declaracion_5ta_external_revenue = getattr(employee_id, 'declaracion_5ta_external_revenue', False)
            record.declaracion_5ta_external_amount = getattr(employee_id, 'declaracion_5ta_external_amount', 0)
            record.declaracion_5ta_retention_partner_id = getattr(employee_id, 'declaracion_5ta_retention_partner_id', False)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    declaracion_5ta_ids = fields.One2many(
        'hr.employee.declaracion.5ta.pe',
        'employee_id',
        string='Declaraciones de 5ta (PE)'
    )
    declaracion_5ta_id = fields.Many2one(
        comodel_name='hr.employee.declaracion.5ta.pe',
        string='Declaración de 5ta Vigente',
        compute='_compute_declaracion_5ta_info',
        store=True,
    )
    declaracion_5ta_fiscal_year = fields.Integer(compute='_compute_declaracion_5ta_info', store=True)
    declaracion_5ta_external_revenue = fields.Boolean(compute='_compute_declaracion_5ta_info', store=True)
    declaracion_5ta_external_amount = fields.Float(compute='_compute_declaracion_5ta_info', store=True)
    declaracion_5ta_retention_partner_id = fields.Many2one(comodel_name='res.partner', compute='_compute_declaracion_5ta_info', store=True)
    family_ids = fields.One2many(
        'hr.employee.family.pe',
        'employee_id',
        string='Familiares (PE)'
    )

    dependent_children_count = fields.Integer(
        string='Número de hijos dependientes',
        compute='_compute_family_stats',
        store=True
    )
    disabled_children_count = fields.Integer(
        string='Número de hijos con discapacidad',
        compute='_compute_family_stats',
        store=True
    )
    student_children_count = fields.Integer(
        string='Número de hijos estudiantes',
        compute='_compute_family_stats',
        store=True
    )

    document_type_id = fields.Many2one(
        comodel_name='l10n_latam.identification.type',
        string='Tipo de documento'
    )
    
    def button_create_declaracion_5ta(self):
        self.ensure_one()
        action = self.sudo().declaracion_5ta_ids.browse()
        action = action.get_formview_action()
        return action

    def _get_current_declaracion_5ta(self):
        #self.ensure_one()
        declaracion_5ta_ids = self.declaracion_5ta_ids
        declaracion_5ta_ids = declaracion_5ta_ids.filtered(lambda r: r.state == 'validated')
        return declaracion_5ta_ids

    @api.depends(
        'declaracion_5ta_ids', 'declaracion_5ta_ids.retention_partner_id',
        'declaracion_5ta_ids.external_revenue', 'declaracion_5ta_ids.external_amount',
    )
    def _compute_declaracion_5ta_info(self):
        for record in self:
            declaracion_5ta_id = record._get_current_declaracion_5ta()
            declaracion_5ta_id = declaracion_5ta_id and declaracion_5ta_id[:1]
            record.declaracion_5ta_id = declaracion_5ta_id
            record.declaracion_5ta_fiscal_year = declaracion_5ta_id.fiscal_year
            record.declaracion_5ta_external_revenue = declaracion_5ta_id.external_revenue
            record.declaracion_5ta_external_amount = declaracion_5ta_id.external_amount
            record.declaracion_5ta_retention_partner_id = declaracion_5ta_id.retention_partner_id

    @api.depends('family_ids.is_child', 'family_ids.is_disabled', 'family_ids.is_student')
    def _compute_family_stats(self):
        for employee in self:
            family_ids = employee.family_ids
            employee.dependent_children_count = sum(1 for fam in family_ids if fam.is_child)
            employee.disabled_children_count = sum(1 for fam in family_ids if fam.is_child and fam.is_disabled)
            employee.student_children_count = sum(1 for fam in family_ids if fam.is_child and fam.is_student)

    def create_unjustified_absences(self, context_day_start, context_day_end, leave_type):
        diff_days = (context_day_end - context_day_start).days
        if diff_days <= 0:
            return
        for i in range(diff_days):
            today = fields.Date.add(context_day_start, days=i)
            today_datetime = fields.Datetime.to_datetime(today)
            time_diff = today_datetime - fields.Datetime.context_timestamp(self, today_datetime).replace(tzinfo=None)
            today_datetime = today_datetime + time_diff
            today_time = fields.Datetime.context_timestamp(self, today_datetime)
            for employee in self:
                resource_calendar_id = employee.resource_calendar_id
                if not resource_calendar_id:
                    continue
                
                # Verificamos si el empleado tenía que trabajar hoy
                attendances = resource_calendar_id._work_intervals_batch(
                    today_time, 
                    fields.Datetime.add(today_time, days=1),
                    resources=employee.resource_id,
                )
                attendances = attendances[employee.resource_id.id]
                if not attendances:
                    continue
    
                # Verificamos si ya tiene una asistencia registrada hoy
                if self.env['hr.attendance'].search_count([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', today_datetime),
                    ('check_in', '<=', fields.Datetime.add(today_datetime, days=1)),
                ]):
                    continue # Sí marcó asistencia
    
                # Verificamos si ya tiene una ausencia aprobada para hoy
                if self.env['hr.leave'].search_count([
                    ('employee_id', '=', employee.id),
                    ('request_date_from', '<=', today),
                    ('request_date_to', '>=', today),
                    ('state', '=', 'validate')
                ]):
                    continue # Ya tiene una ausencia justificada

                #given a range, returns first and last attendance, can be the same
                #attendance_from, attendance_to = self.env['hr.leave']._get_attendances(employee, today, today)
                
                # Si llegamos aquí, el empleado faltó. Creamos la ausencia.
                leave = self.env['hr.leave'].create({
                    'employee_id': employee.id,
                    'holiday_status_id': leave_type.id,
                    'request_date_from': today,
                    'request_date_to': today,
                    #'date_from': today_datetime + timedelta(hours=attendance_from.hour_from),
                    #'date_to': today_datetime + timedelta(hours=attendance_to.hour_to),
                    'name': 'Falta Injustificada (Generada automáticamente)',
                    'state': 'confirm',
                })
                #leave.action_approve()  # Se valida directamente para que impacte en nómina

    @api.model
    def _cron_create_unjustified_absences(self):
        unpaid_leave_type = self.env.ref(
            'mstech_payroll_extend.leave_type_unpaid_pe', 
            raise_if_not_found=False
        )
        if not unpaid_leave_type:
            return
        active_contracts = self.env['hr.contract'].search([('state', '=', 'open'), ('company_id', '!=', False)])
        employees = active_contracts.employee_id
        today = fields.Date.context_today(self)
        employees.create_unjustified_absences(fields.Date.subtract(today, days=1), today, unpaid_leave_type)
    
    def generate_work_entries(self, date_start, date_stop, force=False):
        work_entry_ids = super().generate_work_entries(date_start, date_stop, force=force)
        overtime_request_ids = self.sudo().env['hr.overtime.request'].sudo().search([
            ('employee_id','in',self.ids),
            ('state','=','approved'),
            ('approved_work_entry_id','=',False),
            ('end_datetime','>=',str(date_start)),
            ('start_datetime','<=',str(date_stop)),
        ])
        for overtime_request_id in overtime_request_ids:
            overtime_request_id.approved_work_entry_id = overtime_request_id._action_create_work_entry()
        
        return work_entry_ids
