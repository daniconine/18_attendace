from odoo import models, fields, api, _
from datetime import time, datetime, timedelta
import pytz 



class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

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

    planned_presential = fields.Float(
        string="Horas Presenciales",
        default=0.0,
    )

    planned_virtual = fields.Float(
        string="Horas Virtuales",
        default=0.0,
    )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_duration_hours(self):
        self.ensure_one()
        return max((self.hour_to or 0.0) - (self.hour_from or 0.0), 0.0)

    def _get_week_type_label(self):
        self.ensure_one()

        week_type_selection = dict(self._fields["week_type"].selection)
        return week_type_selection.get(self.week_type, "")

    # -------------------------------------------------------------------------
    # Cálculo de horas planificadas
    # -------------------------------------------------------------------------

    @api.onchange("attendance_type", "hour_from", "hour_to")
    def _onchange_attendance_type_hours(self):
        for rec in self:
            duration = rec._get_duration_hours()

            if rec.attendance_type == "presencial":
                rec.planned_presential = duration
                rec.planned_virtual = 0.0

            elif rec.attendance_type == "virtual":
                rec.planned_presential = 0.0
                rec.planned_virtual = duration

            elif rec.attendance_type in ("descanso", "confianza"):
                rec.planned_presential = 0.0
                rec.planned_virtual = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._set_planned_hours_from_type()
        records._compute_name()
        return records

    def write(self, vals):
        res = super().write(vals)

        fields_to_recompute = {
            "attendance_type",
            "hour_from",
            "hour_to",
        }

        if fields_to_recompute.intersection(vals):
            self._set_planned_hours_from_type()

        if {
            "dayofweek",
            "calendar_id",
            "week_type",
        }.intersection(vals):
            self._compute_name()

        return res

    def _set_planned_hours_from_type(self):
        for rec in self:
            duration = rec._get_duration_hours()

            vals = {}

            if rec.attendance_type == "presencial":
                vals = {
                    "planned_presential": duration,
                    "planned_virtual": 0.0,
                }

            elif rec.attendance_type == "virtual":
                vals = {
                    "planned_presential": 0.0,
                    "planned_virtual": duration,
                }

            elif rec.attendance_type in ("descanso", "confianza"):
                vals = {
                    "planned_presential": 0.0,
                    "planned_virtual": 0.0,
                }

            if vals:
                super(ResourceCalendarAttendance, rec).write(vals)

    # -------------------------------------------------------------------------
    # Nombre automático
    # -------------------------------------------------------------------------

    @api.depends(
        "dayofweek",
        "calendar_id.employee_id",
        "week_type",
        "attendance_type",
    )
    def _compute_name(self):
        """
        Autogenera el nombre:
            Día - Semana - Empleado - Tipo
        """
        day_selection = dict(self._fields["dayofweek"].selection)
        attendance_type_selection = dict(self._fields["attendance_type"].selection)

        for rec in self:
            day_label = day_selection.get(rec.dayofweek, "")
            week_label = rec._get_week_type_label()
            employee = rec.calendar_id.employee_id
            attendance_type_label = attendance_type_selection.get(
                rec.attendance_type,
                "",
            )

            parts = []

            if day_label:
                parts.append(day_label)

            if week_label:
                parts.append(week_label)

            if employee:
                parts.append(employee.name)

            if attendance_type_label:
                parts.append(attendance_type_label)

            rec.name = " - ".join(parts) if parts else False

    @api.onchange(
        "dayofweek",
        "calendar_id",
        "week_type",
        "attendance_type",
    )
    def _onchange_compute_name(self):
        for rec in self:
            rec._compute_name()




#Funcionalidades agregadas al calendario del empleado
class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        required=True,
        tracking=True,
    )

    # -convierte horas deciamales a horas sexagesimales
    def _float_to_time(self, float_hour):
        
        hours = int(float_hour)
        minutes = int(round((float_hour - hours) * 60))

        if minutes == 60:
            hours += 1
            minutes = 0

        hours = min(hours, 23)

        return time(hours, minutes)

    ###convierte la hora a zona horaria lcoal lima
    def _local_to_utc(self, dt, tz_name=False):
        
        self.ensure_one()

        tz_name = tz_name or self.tz or self.env.user.tz or "UTC"
        tz = pytz.timezone(tz_name)

        if dt.tzinfo:
            local_dt = dt.astimezone(tz)
        else:
            local_dt = tz.localize(dt)

        return local_dt.astimezone(pytz.UTC)

    def _get_week_type_for_date(self, current_date, start_date):
        """
        Retorna:
            '0' = Primera semana
            '1' = Segunda semana

        Usa start_date como inicio del ciclo.
        """
        delta_days = (current_date - start_date).days
        week_index = (delta_days // 7) % 2
        return str(week_index)

    def _line_matches_week_type(self, line, current_week_type):
        """
        Valida si una línea del calendario aplica para la semana calculada.

        Si la línea no tiene week_type, se considera aplicable para todas
        las semanas. Esto permite compatibilidad con calendarios simples.
        """
        line_week_type = getattr(line, "week_type", False)

        if not line_week_type:
            return True

        return line_week_type == current_week_type



    # --# Generador
    def action_generate_zattendance(self):
        ZAttendance = self.env["zattendance.day"].with_context(
            skip_zattendance_logic=True
        )

        total_created = 0
        total_updated = 0

        for calendar in self:
            employee = calendar.employee_id
            if not employee:
                continue

            lines = calendar.attendance_ids
            if not lines:
                continue

            dated_lines = lines.filtered(lambda line: line.date_from and line.date_to)

            if dated_lines:
                start_date = min(line.date_from for line in dated_lines)
                end_date = max(line.date_to for line in dated_lines)
            else:
                start_date = fields.Date.today()
                end_date = start_date

            current_date = start_date

            while current_date <= end_date:
                weekday_str = str(current_date.weekday())
                current_week_type = calendar._get_week_type_for_date(
                    current_date,
                    start_date,
                )

                day_lines = lines.filtered(
                    lambda line: line.dayofweek == weekday_str
                    and (not line.date_from or line.date_from <= current_date)
                    and (not line.date_to or line.date_to >= current_date)
                    and calendar._line_matches_week_type(
                        line,
                        current_week_type,
                    )
                )

                if not day_lines:
                    current_date += timedelta(days=1)
                    continue

                start_local = min(
                    datetime.combine(
                        current_date,
                        calendar._float_to_time(line.hour_from),
                    )
                    for line in day_lines
                )

                end_local = max(
                    datetime.combine(
                        current_date,
                        calendar._float_to_time(line.hour_to),
                    )
                    for line in day_lines
                )

                start_dt = calendar._local_to_utc(start_local)
                end_dt = calendar._local_to_utc(end_local)

                planned_presential = sum(
                    line.planned_presential for line in day_lines
                )
                planned_virtual = sum(
                    line.planned_virtual for line in day_lines
                )

                planned_attendance_type = day_lines[0].attendance_type or False

                vals = {
                    "employee_id": employee.id,
                    "date": current_date,
                    "planned_start": fields.Datetime.to_string(start_dt),
                    "planned_end": fields.Datetime.to_string(end_dt),
                    "planned_presential": planned_presential,
                    "planned_virtual": planned_virtual,
                    "planned_attendance_type": planned_attendance_type,
                }

                existing = ZAttendance.search(
                    [
                        ("employee_id", "=", employee.id),
                        ("date", "=", current_date),
                    ],
                    limit=1,
                )

                if existing:
                    existing.write(vals)
                    total_updated += 1
                else:
                    ZAttendance.create(vals)
                    total_created += 1

                current_date += timedelta(days=1)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Generación de asistencia diaria"),
                "message": _(
                    "Se generaron %s registros nuevos y se actualizaron %s registros existentes."
                )
                % (total_created, total_updated),
                "sticky": False,
                "type": "success",
            },
        }