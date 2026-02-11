# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError



class ZLeaveOvertime(models.Model):
    _name = "zleave.overtime"
    _description = "ZLeaveOvertime - Solicitud de Horas Extras"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "name"
    
    name = fields.Char(string="Código", copy=False, readonly=True, tracking=True)
    display_name = fields.Char(compute="_compute_display_name", store=True)
    description = fields.Text(string="Motivo o Descripción")
    approver_id = fields.Many2one("res.users", string="Aprobador", tracking=True)

    company_id = fields.Many2one("res.company", string="Compañía", default=lambda self: self.env.company, required=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, tracking=True)
    employee_job = fields.Many2one(related='employee_id.job_id', string="Cargo del Empl.", readonly=True,)

        
    # Relación con ZAttendance para obtener la información de exceso/defecto y tipo de asistencia
    zattendance_id = fields.Many2one('zattendance.day', 'Registro de Asistencia')
    zattendance_diff = fields.Float(string="Exceso de Horas", 
                                   related='zattendance_id.diff_attendance', readonly=True)
    zattendance_date = fields.Date( string="Fecha de Asistencia",
                        related="zattendance_id.date", store=True)
    zattendance_state = fields.Selection([
        ('conforme', 'Conforme'),
        ('conflicto', 'Conflicto'),
        ('permiso', 'Permiso'),
    ], string="Estado de la Asistencia", related='zattendance_id.state',readonly=True)
    zattendance_type = fields.Selection([
        ('presencial', 'Presencial'),
        ('virtual', 'Virtual'),
        ('descanso', 'Descanso'),
        ('feriado', 'Feriado'),
    ], string="Tipo de Asistencia", related='zattendance_id.planned_attendance_type',readonly=True)
           
    # Horas solicitadas por el empleado
    total_hours_requested = fields.Float(string="Horas Solicitadas", required=True, tracking=True)
    
    # Tipo de pago de horas extras según la normativa peruana
    horas_25 = fields.Float(string="Horas 25%")
    horas_35 = fields.Float(string="Horas 35%")
    horas_200 = fields.Float(string="Horas 200%")
    horas_300 = fields.Float(string="Horas 300%")
    
    # Estado de la solicitud
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Enviado'),
        ('approved', 'Aprobado'),
        ('refused', 'Rechazado'),
        ('cancelled', 'Anulado'),
    ], string="Estado", default='draft', tracking=True)

    ######################################################
    # Creación de la secuencia para horas extras
    @api.model
    def _get_or_create_overtime_sequence(self):
        """Crea la secuencia si no existe (sin XML)"""
        code = "zleave.overtime"
        seq = self.env["ir.sequence"].sudo().search([("code", "=", code)], limit=1)
        if not seq:
            seq = self.env["ir.sequence"].sudo().create({
                "name": "Secuencia Horas Extras ZLeave",
                "code": code,
                "prefix": "HE-",
                "padding": 4,            # HE-0001
                "number_next": 1,
                "number_increment": 1,
                "company_id": False,     # global
            })
        return seq

    @api.model_create_multi
    def create(self, vals_list):
        # Crear la secuencia de horas extras si no existe
        seq = self._get_or_create_overtime_sequence()

        for vals in vals_list:
            # Si no viene con un nombre, generamos uno con la secuencia
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = seq.next_by_id()
           
        # Crear los registros
        records = super(ZLeaveOvertime, self).create(vals_list)
        return records

    # Cálculo del nombre (con la fecha de ZAttendance)
    def _compute_display_name(self):
        for rec in self:
            # Accedemos a la fecha de ZAttendanceDay y la mostramos en el nombre
            attendance_date = rec.zattendance_id.date if rec.zattendance_id else 'Fecha no disponible'
            rec.display_name = f"HE: {rec.employee_id.name} - {attendance_date}"