from odoo import fields, models
from odoo.exceptions import UserError
from odoo.exceptions import AccessError

class ZAttendanceNote(models.Model):
    _name = "zattendance.note"
    _description = "Justificaciones e Incidencias"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    zattendance_day_id = fields.Many2one(
        "zattendance.day",
        string="Asistencia",
        required=True,
        ondelete="cascade",
        index=True,
    )
    
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="zattendance_day_id.company_id",
        store=True,
        readonly=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        related="zattendance_day_id.employee_id",
        store=True,
        readonly=True,
    )

    attendance_date = fields.Date(
        string="Fecha de Asistencia",
        related="zattendance_day_id.date",
        store=True,
        readonly=True,
    )
    
    requested_by = fields.Many2one(
        "res.users",
        string="Solicitante",
        default=lambda self: self.env.user,
        readonly=True,
    )

    category = fields.Selection([
        ("justificacion", "Justificación"),
        ("incidencia", "Incidencia"),
    ], string="Clase", default="incidencia", required=True, tracking=True)

    reason = fields.Selection([
        ("cambio_horario", "Cambio de horario"),        
        ("hextra_comp", "Horas extra generadas para compensar"),
        ("compensacion", "Compensación de horas extras (Descanso)"),
        ("salud", "Salud / Terapia"),
        ("otros", "Otros"),
    ], string="Motivo", default="otros", required=True, tracking=True)

    note = fields.Text(string="Detalle / Sustento", required=True)

    state = fields.Selection([
        ("submitted", "Enviada"),
        ("approved", "Aprobada"),
        ("rejected", "Rechazada"),
    ], string="Estado", default="submitted", tracking=True)

    approved_by = fields.Many2one("res.users", string="Decidido por", readonly=True)
    decision_date = fields.Datetime(string="Fecha decisión", readonly=True)
    n_horas = fields.Float(string="N° Horas Afectadas")
    
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