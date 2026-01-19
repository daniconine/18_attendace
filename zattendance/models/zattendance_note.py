from odoo import fields, models

class ZAttendanceNote(models.Model):
    _name = "zattendance.note"
    _description = "Notas"
    _order = "create_date desc"

    zattendance_day_id = fields.Many2one(
        "zattendance.day",
        string="Asistencia",
        required=True,
        ondelete="cascade",
        index=True,
    )
    note = fields.Text(string="Nota", required=True)
