from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.exceptions import AccessError

class ZAttendanceNote(models.Model):
    _name = "zattendance.note"
    _description = "Justificaciones e Incidencias"
    _inherit = ["mail.thread", "mail.activity.mixin","hr.lock.mixin"]
    _order = "create_date desc"

    zattendance_day_id = fields.Many2one("zattendance.day",string="Asistencia", required=True, 
                                         ondelete="cascade",index=True,)
    
    company_id = fields.Many2one("res.company", string="Compañía",
            related="zattendance_day_id.company_id", store=True,readonly=True,)

    employee_id = fields.Many2one("hr.employee",string="Empleado",
            related="zattendance_day_id.employee_id",store=True,readonly=True,)

    attendance_date = fields.Date(string="Fecha de Asistencia",
                                  related="zattendance_day_id.date",store=True,readonly=True,)
    
    requested_by = fields.Many2one("res.users",string="Solicitante",default=lambda self: self.env.user,readonly=True,)

    category = fields.Selection(
        [   ("justificacion", "Justificación"),
            ("incidencia", "Incidencia"),
            ("otros", "Otros"),
        ],
        string="Categoria",compute="_compute_category",store=True,tracking=True,)

    reason = fields.Selection([
        ("cambio_horario", "Cambio de horario"),        
        ("hextra_comp", "Generación de horas compensatorias"),
        ("compensacion", "Uso de horas compensatorias (Descanso)"),
        ("salud", "Salud / Terapia"),
        ("otros", "Otros"),
    ], string="Motivo", default="otros", required=True, tracking=True)

    note = fields.Text(string="Detalle / Sustento", required=True)

    state = fields.Selection([
        ("submitted", "Enviada"),
        ("approved", "Aprobada"),
        ("rejected", "Rechazada"),
    ], string="Estado", default="submitted", tracking=True)

    approved_by = fields.Many2one("res.users", string="Resuelto por:", readonly=True)
    decision_date = fields.Datetime(string="Fecha de resolución", readonly=True)
    n_horas = fields.Float(string="N° Horas Afectadas")
    
    comp_hours_balance = fields.Float(string="Saldo de horas compensatorias",
                        related="employee_id.comp_hours_balance",readonly=True,)
    
    compensation_date = fields.Date(string="Día a recuperar / descansar",tracking=True, 
             help="Fecha relacionada con la generación o uso de horas compensatorias.",)
    
    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Solo puedes aprobar solicitudes en estado 'Enviada'.")
        self.write({
            "state": "approved",
            "approved_by": self.env.user.id,
            "decision_date": fields.Datetime.now(),
        })

    def action_reject(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Solo puedes rechazar solicitudes en estado 'Enviada'.")
        self.write({
            "state": "rejected",
            "approved_by": self.env.user.id,
            "decision_date": fields.Datetime.now(),
        })
    
        
    @api.depends("reason")
    def _compute_category(self):
        for rec in self:
            if rec.reason in ("cambio_horario", "hextra_comp"):
                rec.category = "incidencia"
            elif rec.reason in ("compensacion", "salud"):
                rec.category = "justificacion"
            elif rec.reason == "otros":
                rec.category = "otros"
            else:
                rec.category = False
    
    #######################
    # Le decimos que ahora depende del estado para marcarse solo
    is_locked = fields.Boolean(string="Bloqueado",
            compute="_compute_is_locked",store=True, readonly=False,tracking=True)

    @api.depends("state")
    def _compute_is_locked(self):
        for rec in self:
            rec.is_locked = rec.state in ("approved", "rejected")