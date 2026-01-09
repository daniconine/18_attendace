from odoo import models, fields, api, _
from datetime import time, datetime, timedelta
import pytz 

class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    attendance_type = fields.Selection(
        [
            ("presencial", "Asistencia Presencial"),
            ("virtual", "Asistencia Virtual"),
            ("descanso", "Descanso"),            
            ("confianza", "Confianza (exento control)"),
        ],
        string="Tipo de asistencia",
        help="Tipo de asistencia planificada para este tramo horario.",
    )

    planned_presential = fields.Float(string="Horas Presenciales", default=0)
    planned_virtual = fields.Float(string="Horas Virtuales", default=0)

       

    #autogenera el nombre de la asistencia dia del ekmpleado
    @api.depends('dayofweek', 'calendar_id.employee_id')
    def _compute_name(self):
        """Autogenera el nombre: Día - Empleado"""
        day_selection = dict(self._fields['dayofweek'].selection)
        for rec in self:
            day_label = day_selection.get(rec.dayofweek, False)
            employee = rec.calendar_id.employee_id
            if day_label and employee:
                rec.name = f"{day_label} – {employee.name}"
            elif day_label:
                rec.name = day_label


    @api.onchange('dayofweek', 'calendar_id')
    def _onchange_compute_name(self):
        """Mantiene coherencia en modo edición UI"""
        for rec in self:
            rec._compute_name()



##Resoruce_Calendar
class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'
    
    employee_id = fields.Many2one(
    "hr.employee",
    string="Empleado",
    required=True,        
    tracking=True,
    )
        
    # --- Helper interno ---
    def _float_to_time(self, float_hour):
        hours = int(float_hour)
        minutes = int(round((float_hour - hours) * 60))
        return time(hours, minutes)

    def _local_to_utc(self, dt, tz_name=False):
        """Convierte un datetime 'local' a UTC según la tz del calendario o usuario."""
        self.ensure_one()
        tz_name = tz_name or self.tz or self.env.user.tz or 'UTC'
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            local_dt = dt.astimezone(tz)
        else:
            local_dt = tz.localize(dt)
        return local_dt.astimezone(pytz.UTC)
    
    #Generador
    def action_generate_zattendance(self):
        ZAttendance = self.env['zattendance.day'].with_context(skip_zattendance_logic=True)


        total_created = 0
        total_updated = 0

        for calendar in self:
            employee = calendar.employee_id
            if not employee:
                continue

            lines = calendar.attendance_ids
            if not lines:
                continue

            dated_lines = lines.filtered(lambda l: l.date_from and l.date_to)
            if dated_lines:
                start_date = min(l.date_from for l in dated_lines)
                end_date = max(l.date_to for l in dated_lines)
            else:
                start_date = fields.Date.today()
                end_date = start_date

            current_date = start_date
            while current_date <= end_date:
                weekday_str = str(current_date.weekday())

                day_lines = lines.filtered(
                    lambda l: l.dayofweek == weekday_str
                    and (not l.date_from or l.date_from <= current_date)
                    and (not l.date_to or l.date_to >= current_date)
                )
                if not day_lines:
                    current_date += timedelta(days=1)
                    continue

                start_local = min(
                    datetime.combine(current_date, calendar._float_to_time(l.hour_from))
                    for l in day_lines
                )
                end_local = max(
                    datetime.combine(current_date, calendar._float_to_time(l.hour_to))
                    for l in day_lines
                )

                start_dt = calendar._local_to_utc(start_local)
                end_dt = calendar._local_to_utc(end_local)

                planned_presential = sum(l.planned_presential for l in day_lines)
                planned_virtual = sum(l.planned_virtual for l in day_lines)
                planned_attendance_type = day_lines[0].attendance_type or False

                vals = {
                    'employee_id': employee.id,
                    'date': current_date,
                    'planned_start': fields.Datetime.to_string(start_dt),
                    'planned_end': fields.Datetime.to_string(end_dt),
                    'planned_presential': planned_presential,
                    'planned_virtual': planned_virtual,
                    'planned_attendance_type': planned_attendance_type,
                }

                existing = ZAttendance.search([
                    ('employee_id', '=', employee.id),
                    ('date', '=', current_date),
                ], limit=1)

                if existing:
                    existing.write(vals)
                    total_updated += 1
                else:
                    ZAttendance.create(vals)
                    total_created += 1

                current_date += timedelta(days=1)

        # 🔔 Notificación al usuario
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Generación de asistencia diaria'),
                'message': _(
                    'Se generaron %s registros nuevos y se actualizaron %s registros existentes.'
                ) % (total_created, total_updated),
                'sticky': False,
                'type': 'success',
            }
        }