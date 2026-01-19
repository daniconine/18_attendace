##=||=||=||=||=||=||=||=||=||=||=||=||=
###Desarrollo de Módulode entrada de trabajo Zattendance

from odoo import api, fields, models
import logging
from odoo.exceptions import UserError
from datetime import timedelta
_logger = logging.getLogger(__name__)

#Registro unico de asistencia por empelado
class ZAttendanceDay(models.Model):
    _name = "zattendance.day"
    _description = "ZAttendance - Asistencia diaria consolidada"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, employee_id"

    
    name = fields.Char(string="Nombre", compute="_compute_name", store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one( "res.company", string="Compañía",
                default=lambda self: self.env.company, required=True, )

    employee_id = fields.Many2one("hr.employee",string="Empleado", readonly=True,
                required=True, tracking=True, )
    date = fields.Date(string="Fecha", required=True, readonly=True, tracking=True, )
    
    weekday = fields.Selection(
        [
            ("0", "Lunes"),("1", "Martes"), ("2", "Miércoles"), ("3", "Jueves"),
            ("4", "Viernes"), ("5", "Sábado"), ("6", "Domingo"), ],
        string="Día", compute="_compute_weekday", store=True, )
    
    # Unicidad: 1 registro por empleado por día
    _sql_constraints = [
        (
            "zattendance_day_unique_employee_date",
            "unique(employee_id, date)",
            "Ya existe un registro de asistencia para este empleado en esta fecha.",
        )]

    #calculo del nombre
    @api.depends("employee_id", "date")
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.date:
                rec.name = f"{rec.employee_id.name} / {fields.Date.to_string(rec.date)}"
            elif rec.employee_id:
                rec.name = rec.employee_id.name
            else:
                rec.name = False

    @api.depends("date")
    def _compute_weekday(self):
        for rec in self:
            if rec.date:
                # date.weekday(): lunes = 0 ... domingo = 6
                rec.weekday = str(rec.date.weekday())
            else:
                rec.weekday = False


    #################################################################    
    # Asistencia Planificado (Horario)
    planned_start = fields.Datetime(string="Hora Entrada Horario", tracking=True)
    planned_end = fields.Datetime(string="Hora Salida Horario", tracking=True)

    planned_presential = fields.Float(string="Horas Presenciales Planific", tracking=True, default=0)
    planned_virtual = fields.Float(string="Horas Virtuales Planific", tracking=True, default=0)
    planned_total = fields.Float(string="Horas Totales Planific", compute="_compute_planned_total", store=True, default=0)

    planned_attendance_type = fields.Selection(
        [
            ("presencial", "Asistencia Presencial"),
            ("virtual", "Asistencia Virtual"),
            ("descanso", "Descanso"),
            ("feriado", "Feriado"),
            ("vacaciones", "Vacaciones"),
            ("lic_con_goce", "Lic con goce de haber"),
            ("lic_sin_goce", "Lic sin goce de haber"),
            ("confianza", "Confianza (exento control)"),
        ],
        string="Tipo de Asistencia Asignado",
        tracking=True,)

    # Asisetncia Real (desde módulo de asistencia - por ahora editable)
   
    actual_first_check_in = fields.Datetime(string="Hora Entrada Real", readonly=True)
    actual_last_check_out = fields.Datetime(string="Hora Salida Real", readonly =True)

    actual_presential = fields.Float(string="Horas Presenciales Reales", readonly=True)
    actual_virtual = fields.Float(string="Horas Virtuales Reales",readonly=True)
    actual_total = fields.Float(string="Horas Totales Reales",compute="_compute_actual_total", store=True)

    
    tipo_asistencia = fields.Selection(
        [
            ("presencial", "Asistencia Presencial"),
            ("virtual", "Asistencia Virtual"),
            ("inasistencia", "Inasistencia"),
        ],
        string="Tipo de Asistencia Calculada",
        compute="_compute_tipo_asistencia", store=True, tracking=True,)

    #Calculos para total de horas
    @api.depends("planned_presential", "planned_virtual")
    def _compute_planned_total(self):
        for rec in self:
            rec.planned_total = rec.planned_presential + rec.planned_virtual
    
    @api.depends("actual_presential", "actual_virtual")
    def _compute_actual_total(self):
        for rec in self:
            rec.actual_total = rec.actual_presential + rec.actual_virtual
            
       
    # Exceso o Defecto horas independiente para la nómina
    diff_attendance = fields.Float(string="Exceso/Defecto Horas", tracking=True, store=True, default=0)

    def action_recalcular(self):
        for rec in self:
            Attendance = self.env['hr.attendance']

            # Sumar horas presenciales netas
            attendances_presential = Attendance.search([
                ('employee_id', '=', rec.employee_id.id),
                ('check_in_date', '=', rec.date),
                ('modalidad', '=', 'Huellero'),
            ])
            rec.actual_presential = sum(att.horas_neto for att in attendances_presential)

            # Sumar horas virtuales netas
            attendances_virtual = Attendance.search([
                ('employee_id', '=', rec.employee_id.id),
                ('check_in_date', '=', rec.date),
                ('modalidad', '=', 'Virtual'),
            ])
            rec.actual_virtual = sum(att.horas_neto for att in attendances_virtual)

            # Cálculo de las horas totales reales
            rec.actual_total = rec.actual_presential + rec.actual_virtual

            # Recalcular exceso/defecto de horas después de recalcular las horas reales
            if rec.state != "permiso":  # Si el estado no es "permiso", calculamos el exceso/defecto
                rec.diff_attendance = rec.actual_total - rec.planned_total  # Diferencia entre horas reales y planificadas

            # 1ra marcación y última marcación
            attendances_day = Attendance.search([
                ('employee_id', '=', rec.employee_id.id),
                ('check_in_date', '=', rec.date),
            ])

            if attendances_day:
                # Primera entrada del día = mínimo check_in
                checkins = [dt for dt in attendances_day.mapped('check_in') if dt]
                rec.actual_first_check_in = min(checkins) if checkins else False

                # Última salida del día = máximo check_out (solo donde exista check_out)
                checkouts = [dt for dt in attendances_day.mapped('check_out') if dt]
                rec.actual_last_check_out = max(checkouts) if checkouts else False
            else:
                rec.actual_first_check_in = False
                rec.actual_last_check_out = False


    
    #Tipo_Assitencia        
    @api.depends('actual_presential', 'actual_virtual')
    def _compute_tipo_asistencia(self):
        """Calcula el tipo de asistencia basado en las horas reales."""
        for rec in self:
            if self.env.context.get('skip_zattendance_logic'):
                rec.tipo_asistencia = False 
                continue
            
            # Si tenemos horas presenciales y virtuales, primero asignamos 'presencial' si hay horas presenciales
            if rec.actual_presential > 0 and rec.actual_virtual > 0:
                rec.tipo_asistencia = 'presencial'  # Por defecto, asignamos presencial si ambos están presentes

            # Si solo hay horas presenciales
            elif rec.actual_presential > 0:
                rec.tipo_asistencia = 'presencial'

            # Si solo hay horas virtuales
            elif rec.actual_virtual > 0:
                rec.tipo_asistencia = 'virtual'

            # Si no hay horas presenciales ni virtuales, asignamos 'inasistencia'
            else:
                rec.tipo_asistencia = 'inasistencia'

            
    # Adicionales de control a la asistencia por estado y permisos
    # (Permiso se determina SOLO por permission_id aprobado)
    state = fields.Selection(
        [
            ("conforme", "Conforme"),
            ("conflicto", "Conflicto"),
            ("permiso", "Permiso"),
        ],
        string="Estado",store=True, tracking=True, )

    late_min = fields.Integer( string="Tardanza (min)", compute="_compute_late_min",
                        store=True,default=0, )
    permiso_late = fields.Boolean(string="Permiso de Tardanza", tracking=True)
    note_ids = fields.One2many("zattendance.note", "zattendance_day_id", string="Notas")
    # Permiso de tardanza (si quieres: si el día está en permiso, no hay tardanza)
    @api.depends("planned_attendance_type", "planned_start", "actual_first_check_in", "permiso_late", "state")
    def _compute_late_min(self):
        tolerance = 15
        for rec in self:
            # Si el día es permiso o tiene permiso de tardanza, no hay tardanza
            if rec.state == "permiso" or rec.permiso_late:
                rec.late_min = 0
                continue

            can_compute = (
                rec.planned_attendance_type in ("presencial", "virtual")
                and rec.planned_start
                and rec.actual_first_check_in
            )
            if not can_compute:
                rec.late_min = 0
                continue

            minutes = int((rec.actual_first_check_in - rec.planned_start).total_seconds() // 60)
            rec.late_min = minutes if minutes > tolerance else 0
        
    ##### Matriz de conflicto + evaluación
    def _is_conflict_by_matrix(self, planned, calculated):
        # Matriz según tu tabla (solo marcamos los SI)
        conflict_matrix = {
            "presencial": {
                "presencial": False,
                "virtual": True,
                "inasistencia": True,
            },
            "virtual": {
                "presencial": False,
                "virtual": False,
                "inasistencia": True,
            },
            # Todo lo demás nunca es conflicto:
            "descanso": {"presencial": False, "virtual": False, "inasistencia": False},
            "feriado": {"presencial": False, "virtual": False, "inasistencia": False},
            "vacaciones": {"presencial": False, "virtual": False, "inasistencia": False},
            "lic_con_goce": {"presencial": False, "virtual": False, "inasistencia": False},
            "lic_sin_goce": {"presencial": False, "virtual": False, "inasistencia": False},
            "confianza": {"presencial": False, "virtual": False, "inasistencia": False},
        }
        planned_map = conflict_matrix.get(planned)
        if not planned_map:
            return False
        return bool(planned_map.get(calculated, False))

    def _evaluate_state_from_matrix(self):
        """
        Reglas:
        - Si hay permission_id aprobado => state = 'permiso' (siempre)
        - Si falta planned_attendance_type o tipo_asistencia => no tocar
        - Caso contrario => conflicto/conforme por matriz
        """
        for rec in self:
            # Si viene de solicitud aprobada, manda permiso (y no se evalúa matriz)
            if rec.state == "permiso":
                continue

            # Sin permiso aprobado => matriz normal
            if not rec.planned_attendance_type or not rec.tipo_asistencia:
                continue

            if rec._is_conflict_by_matrix(rec.planned_attendance_type, rec.tipo_asistencia):
                rec.state = "conflicto"
            else:
                rec.state = "conforme"


    ########################
    # Disparadores del state
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get("skip_zattendance_logic"):
            return records

        records._evaluate_state_from_matrix()
        return records


    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("skip_zattendance_logic"):
            return res

        # Incluimos permission_id para reevaluar cuando se vincule/desvincule
        watched = {
            "planned_attendance_type",
            "actual_presential",
            "actual_virtual",
            "recalculated",
            "tipo_asistencia",
            
            "permiso_late",
        }
        if watched.intersection(vals.keys()):
            self._evaluate_state_from_matrix()

        return res
    
    ######## Accion Recalcular del cron para el dia anterior
    @api.model
    def cron_recalcular_dia_anterior(self):
        today = fields.Date.context_today(self.with_context(tz='America/Lima'))
        yesterday = today - timedelta(days=1)

        days = self.search([('date', '=', yesterday), ('active', '=', True)])
        if days:
            days.action_recalcular()