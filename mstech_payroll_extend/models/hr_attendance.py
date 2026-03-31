from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    late_minutes = fields.Integer(string="Minutos de Tardanza", compute='_compute_late_minutes', store=True)
    linked_leave_id = fields.Many2one('hr.leave', string="Ausencia generada por tardanza", readonly=True)

    overtime_minutes = fields.Integer(string="Minutos de hora extra", compute='_compute_overtime_minutes', store=True)
    linked_overtime_ids = fields.One2many('hr.overtime.request', 'attendance_id', string="Horas Extras Generadas", readonly=True)

    @api.depends('employee_id', 'check_in')
    def _compute_late_minutes(self):
        """
        NOTE: salida antes de hora no está contemplado
        TODO: contrato debe estar en progreso?
        """
        for rec in self:
            rec.late_minutes = 0
            if not rec.employee_id or not rec.check_in:
                continue

            contract = rec.employee_id.contract_id
            calendar = contract.resource_calendar_id if contract else None
            if not calendar:
                continue

            check_in_dt = fields.Datetime.context_timestamp(rec, rec.check_in)
            weekday = check_in_dt.weekday()

            attendances = calendar.attendance_ids.filtered(lambda a: int(a.dayofweek) == weekday)

            late_minutes = {}
            for att in attendances:
                hour_from = att.hour_from
                start_hour = int(hour_from)
                start_minute = int((hour_from - start_hour) * 60)
                shift_start = check_in_dt.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                delta = (check_in_dt - shift_start).total_seconds() / 60
                late_minutes.update({
                    abs(delta): delta,
                })
            #aquel con la menor diferencia (+ o -) supone ser el horario adecuado a comparar
            nearest = min(late_minutes) if late_minutes else None
            if not nearest:
                continue
            rec.late_minutes = late_minutes[nearest] if late_minutes[nearest] > 0 else 0

    @api.depends('employee_id', 'check_out')
    def _compute_overtime_minutes(self):
        """
        NOTE: Ingreso antes de la hora no está contemplado
        TODO: contrato debe estar en progreso?
        """
        for rec in self:
            rec.overtime_minutes = 0
            if not rec.employee_id or not rec.check_out:
                continue

            contract = rec.employee_id.contract_id
            calendar = contract.resource_calendar_id if contract else None
            if not calendar:
                continue

            check_out_dt = fields.Datetime.context_timestamp(rec, rec.check_out)
            weekday = check_out_dt.weekday()

            attendances = calendar.attendance_ids.filtered(lambda a: int(a.dayofweek) == weekday)
            
            overtime_minutes = {}
            for att in attendances:
                hour_to = att.hour_to
                end_hour = int(hour_to)
                end_minute = int((hour_to - end_hour) * 60)
                shift_end = check_out_dt.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
                delta = (check_out_dt - shift_end).total_seconds() / 60
                overtime_minutes.update({
                    abs(delta): delta,
                })
            #aquel con la menor diferencia (+ o -) supone ser el horario adecuado a comparar
            nearest = min(overtime_minutes) if overtime_minutes else None
            if not nearest:
                continue
            rec.overtime_minutes = overtime_minutes[nearest] if overtime_minutes[nearest] > 0 else 0

    # --- MÉTODO CREATE: PARA LÓGICA DE TARDANZAS ---
    @api.model_create_multi
    def create(self, vals_list):
        # Primero, creamos los registros de asistencia como lo hace Odoo
        records = super().create(vals_list)

        #Cuando se importa tambien procesar horas extra
        attendance_import = self.env.context.get('attendance_import')
        # Ahora, para cada nuevo registro (check-in), ejecutamos la lógica de tardanza
        for rec in records:
            rec._handle_tardiness()
            if attendance_import:
                rec._handle_overtime()
            
        return records

    # --- MÉTODO WRITE: PARA LÓGICA DE HORAS EXTRAS ---
    def write(self, vals):
        # Ejecutamos el write original para guardar el check_out
        res = super().write(vals)

        # Solo si se está actualizando el check_out, procesamos las horas extras
        if 'check_out' in vals:
            for rec in self.filtered(lambda a: a.check_in and a.check_out):
                rec._handle_overtime()
        
        return res

    def _handle_tardiness(self):
        """
        ERROR: si se registra más de 1 entrada en un día que solo tiene un horario (p.e. sábado solo turno mañana)
               intenta crear doble tardanza para un mismo horario
        """
        self.ensure_one()
        # Si no hubo tardanza o ya se generó una ausencia, no hacemos nada.
        if self.late_minutes <= 0 or self.linked_leave_id:
            return

        contract = self.employee_id.contract_id
        if not contract:
            return

        # Personal de confianza no genera tardanzas
        is_trusted_employee = contract.is_trusted_employee
        if is_trusted_employee:
            return

        calendar = contract.resource_calendar_id if contract else None
        if not calendar:
            return

        check_in_dt = fields.Datetime.context_timestamp(self, self.check_in)
        weekday = check_in_dt.weekday()

        attendances = calendar.attendance_ids.filtered(lambda a: int(a.dayofweek) == weekday)

        late_minutes = {}
        for att in attendances:
            hour_from = att.hour_from
            start_hour = int(hour_from)
            start_minute = int((hour_from - start_hour) * 60)
            shift_start = check_in_dt.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            delta = (check_in_dt - shift_start).total_seconds() / 60
            late_minutes.update({
                abs(delta): check_in_dt.replace(hour=start_hour, minute=int(hour_from - start_hour) * 60, second=0, microsecond=0),
            })
        #aquel con la menor diferencia (+ o -) supone ser el horario adecuado a comparar
        nearest = min(late_minutes) if late_minutes else None
        if not nearest:
            return
        calendar_check_in = late_minutes[nearest]
        calendar_check_in = (calendar_check_in+timedelta(hours=5)).replace(tzinfo=None)
            

        tolerance = contract.overtime_tolerance_minutes or 0    
        # 2. Comparamos la tardanza con la tolerancia. Si es menor o igual, no hacemos nada.
        if self.late_minutes <= tolerance:
            return

        # 3. Determinamos el tipo de ausencia a crear basado en la duración de la tardanza.
        leave_type = None
        if self.late_minutes <= 60:
            leave_type = contract.tardiness_type_1h
        elif self.late_minutes <= 120:
            leave_type = contract.tardiness_type_2h
        else:
            leave_type = contract.tardiness_type_more

        # 4. Si no hay un tipo de ausencia configurado para ese tramo, no continuamos.
        #    Esto es importante para evitar errores si el contrato no está completamente configurado.
        if not leave_type:
            return

        # Creamos la ausencia para que RRHH la valide
        leave_vals = {
            'employee_id': self.employee_id.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': self.check_in.date(),
            'request_date_to': self.check_in.date(),
            'request_hour_from': (calendar_check_in.hour - 5) + (calendar_check_in.minute / 60),
            'request_hour_to': (self.check_in.hour - 5) + (self.check_in.minute / 60),
            'name': f'Tardanza automática: {self.late_minutes} min',
            # ¡IMPORTANTE! Se crea en estado 'A Aprobar' para que RRHH pueda validarla o rechazarla.
            'state': 'confirm',
            # V18
            'request_unit_hours': True,
        }
        leave = self.env['hr.leave'].create(leave_vals)
        self.linked_leave_id = leave.id

    def _handle_overtime(self):
        self.ensure_one()
        # Si no hay sobretiempo o ya se generaron solicitudes, no hacemos nada.
        if self.overtime_minutes <= 0 or self.linked_overtime_ids:
            return

        contract = self.employee_id.contract_id
        if not contract:
            return

        # Personal de confianza no genera horas extras
        is_trusted_employee = contract.is_trusted_employee
        if is_trusted_employee:
            return

        tolerance = contract.overtime_generation_tolerance or 0
        if self.overtime_minutes <= tolerance:
            return

        overtime_model = self.env['hr.overtime.request']
        shift_end = self.check_out - timedelta(minutes=self.overtime_minutes)

        # Dividimos el sobretiempo en los dos tramos
        minutes_25 = min(self.overtime_minutes, 120)
        minutes_35 = self.overtime_minutes - minutes_25

        # Tramo 1: Horas al 25%
        if minutes_25 > 0:
            start_dt = shift_end
            end_dt = start_dt + timedelta(minutes=minutes_25)
            # Verificamos si es nocturno
            is_night = start_dt.hour >= 22 or start_dt.hour < 6
            overtime_type = 'night_25' if is_night else '25'
            
            overtime_model.create({
                'employee_id': self.employee_id.id,
                'attendance_id': self.id,
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'overtime_type': overtime_type,
                'reason': f'Generado automáticamente por asistencia (Total HE: {self.overtime_minutes} min)',
                'state': 'draft',
            })
        
        # Tramo 2: Horas al 35%
        if minutes_35 > 0:
            start_dt = shift_end + timedelta(minutes=tolerance + 120)
            end_dt = start_dt + timedelta(minutes=minutes_35)
            is_night = start_dt.hour >= 22 or start_dt.hour < 6
            overtime_type = 'night_35' if is_night else '35'
            
            overtime_model.create({
                'employee_id': self.employee_id.id,
                'attendance_id': self.id,
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'overtime_type': overtime_type,
                'reason': f'Generado automáticamente por asistencia (Total HE: {self.overtime_minutes} min)',
                'state': 'draft',
            })
    
