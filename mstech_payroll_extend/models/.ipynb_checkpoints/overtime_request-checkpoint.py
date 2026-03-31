from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from datetime import timedelta


class HrOvertimeRequest(models.Model):
    _name = 'hr.overtime.request'
    _description = 'Solicitud de Horas Extras'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True,
                       default=lambda self: 'Nuevo')
    attendance_id = fields.Many2one(string="Asistencia", comodel_name="hr.attendance", ondelete="cascade")
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    start_datetime = fields.Datetime(string='Inicio', required=True)
    end_datetime = fields.Datetime(string='Fin', required=True)
    overtime_type = fields.Selection([
    ('25', 'Hora Extra 25%'),
    ('35', 'Hora Extra 35%'),
    ('night_25', 'Hora Extra Nocturna 25%'),
    ('night_35', 'Hora Extra Nocturna 35%'),
    ('holiday', 'Hora Extra en Feriado 100%'),
    ('sunday', 'Hora Extra en Domingo 100%'),
    ('compensatory', 'Trabajo Compensatorio'),
    ('other', 'Otro')
], string='Tipo de Hora Extra', required=True)
    reason = fields.Text(string='Motivo')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Solicitado'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado')
    ], string='Estado', default='draft', tracking=True)
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsable de aprobación',
        default=lambda self: self.employee_id.parent_id.user_id,
        readonly=True
    )
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Tipo de Entrada de Trabajo',
                                         help='Tipo de entrada de trabajo correspondiente a la hora extra.',
                                         compute='_compute_work_entry_type_id', store=True, readonly=False, inverse='_inverse_work_entry_type_id')
    approved_work_entry_id = fields.Many2one('hr.work.entry', string='Entrada generada', readonly=True)


    @api.onchange('overtime_type')
    def _onchange_overtime_type(self):
        if self.overtime_type:
            # Buscamos el tipo de entrada de trabajo que coincida con el código seleccionado
            work_entry_type = self.env['hr.work.entry.type'].search([
                ('pe_overtime_code', '=', self.overtime_type)
            ], limit=1)
            
            # Asignamos el resultado (será False si no encuentra nada)
            self.work_entry_type_id = work_entry_type
        else:
            self.work_entry_type_id = False

    @api.depends('overtime_type')
    def _compute_work_entry_type_id(self):
        for record in self:
            record._onchange_overtime_type()

    def _inverse_work_entry_type_id(self):
        pass

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.overtime.request') or 'Nuevo'
        return super().create(vals)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def _action_create_work_entry(self):
        self.ensure_one()
        # Crear work.entry
        work_entry = self.env['hr.work.entry'].create({
            'name': str(self.work_entry_type_id.name) + ': ' + self.employee_id.name,
            'employee_id': self.employee_id.id,
            'date_start': self.start_datetime,
            'date_stop': self.end_datetime,
            'work_entry_type_id': self.work_entry_type_id.id,
            'overtime_request_id': self.id,
            'contract_id': self.employee_id.contract_id.id,
            'state': 'draft'
        })
        return work_entry

    def action_approve(self):
        for request in self:
            if not request.work_entry_type_id:
                raise ValidationError("Debe seleccionar el tipo de entrada de trabajo.")
    
            contract = request.employee_id.contract_id
            if not contract:
                raise ValidationError("El empleado no tiene un contrato activo.")
    
            calendar = contract.resource_calendar_id
            if not calendar:
                raise ValidationError("El contrato no tiene un horario definido.")

            # 🔒 Validación: Si es tipo 25%, no puede exceder 2 horas
            if request.overtime_type == '25':
                duration = (request.end_datetime - request.start_datetime).total_seconds() / 3600.0
                if duration > 2.0:
                    raise ValidationError("Las horas extra al 25% no pueden superar las 2 horas.")
    
            weekday = request.start_datetime.weekday()
            attendances = calendar.attendance_ids.filtered(lambda a: int(a.dayofweek) == weekday)
    
            # Validar que la hora extra esté completamente fuera del horario regular
            for att in attendances:
                att_start = fields.Datetime.from_string(
                    f"{request.start_datetime.date()} {int(att.hour_from):02d}:{int((att.hour_from % 1) * 60):02d}:00")
                att_end = fields.Datetime.from_string(
                    f"{request.start_datetime.date()} {int(att.hour_to):02d}:{int((att.hour_to % 1) * 60):02d}:00")
    
                # Si hay cualquier cruce con el horario
                if request.start_datetime < att_end and request.end_datetime > att_start:
                    raise ValidationError("La hora extra se cruza con el horario laboral del día.")

            if request.overtime_type == 'compensatory':
                # 1. Calcular la duración en horas
                duration_td = request.end_datetime - request.start_datetime
                duration_hours = duration_td.total_seconds() / 3600.0

                if duration_hours <= 0:
                    raise ValidationError("La duración del trabajo compensatorio debe ser positiva.")

                # 2. Actualizar el saldo en el contrato del empleado
                new_balance = contract.compensatory_hours_balance + duration_hours
                contract.write({'compensatory_hours_balance': new_balance})
                
                # 3. Registrar un mensaje en el chatter del contrato para auditoría
                contract.message_post(
                    body=f"Se acreditaron <b>{duration_hours:.2f} horas</b> al saldo de horas compensatorias "
                         f"desde la solicitud <b>{request.name}</b>. Nuevo saldo: {new_balance:.2f} horas."
                )    

            work_entry = self._action_create_work_entry()
            request.write({
                'approved_work_entry_id': work_entry.id,
                'state': 'approved'
            })

    def _reverse_compensatory_hours(self):
        for request in self.filtered(lambda r: r.state == 'approved' and r.overtime_type == 'compensatory'):
            contract = request.employee_id.contract_id
            if contract:
                duration_td = request.end_datetime - request.start_datetime
                duration_hours = duration_td.total_seconds() / 3600.0
                
                new_balance = contract.compensatory_hours_balance - duration_hours
                contract.write({'compensatory_hours_balance': new_balance})
                
                contract.message_post(
                    body=f"Se revirtieron <b>{duration_hours:.2f} horas</b> del saldo de horas compensatorias "
                         f"debido a la cancelación/rechazo de la solicitud <b>{request.name}</b>. Nuevo saldo: {new_balance:.2f} horas."
                )
            
            # También eliminamos la entrada de trabajo generada para mantener la consistencia
            if request.approved_work_entry_id:
                request.approved_work_entry_id.action_cancel() # Lo cancelamos
                request.approved_work_entry_id.unlink() # Y lo borramos

    def action_reject(self):
        self._reverse_compensatory_hours()
        self.write({'state': 'rejected'})
        
    def action_reset_to_draft(self):
        self._reverse_compensatory_hours()
        self.write({'state': 'draft'})
