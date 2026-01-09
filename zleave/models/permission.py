# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ZleavePermission(models.Model):
    _name = "zleave.permission"
    _description = "ZleavePErmission - Permisos"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "name" 

    
    name = fields.Char( string="Código",copy=False,readonly=True,tracking=True,)
    display_name = fields.Char(compute="_compute_display_name", store=False)
    description = fields.Text(string="Descripción")
    company_id = fields.Many2one("res.company", string="Compañía",
                default=lambda self: self.env.company,required=True, readonly=True,)
    employee_id = fields.Many2one("hr.employee",string="Empleado",required=True,     
                    tracking=True,)
    requested_by_id = fields.Many2one( "res.users", string="Solicitado por",
                    default=lambda self: self.env.user,readonly=True, tracking=True,)

    approver_id = fields.Many2one("res.users", string="Aprobador", tracking=True, readonly=True,
        domain="[('share','=',False), ('company_ids','in', company_id)]",
        help="Por defecto: employee.leave_manager_id (Aprobador de Ausencias) y fallback a jefe directo.",
    )
    
    date_from = fields.Date(string="Desde", required=True, tracking=True)
    date_to = fields.Date(string="Hasta", required=True, tracking=True)
    
    duration_days = fields.Float(string="Solicitado (días)", compute="_compute_duration_days", store=True)

    type_permission = fields.Selection(
        [   ('sin_goce', 'Licencia Sin Goce (S.P.)/Ausencia'),
            ('con_goce', 'Licencia Con Goce (S.I)/Permiso'),            
        ],
        string="Ausencia/Permiso", tracking=True, )
    
    suspension_perfecta = fields.Selection([
        ('1', '1 - S.P. SANCIÓN DISCIPLINARIA'),
        ('2', '2 - S.P. EJERCICIO DERECHO HUELGA'),
        ('3', '3 - S.P. DETENCIÓN DEL TRABAJADOR'),
        ('4', '4 - S.P. INHABILITACIÓN ADMINISTRATIVA O JUDICIAL'),
        ('5', '5 - S.P. PERMISO O LICENCIA SIN GOCE DE HABER'),
        ('6', '6 - S.P. CASO FORTUITO O FUERZA MAYOR'),
        ('7', '7 - S.P. FALTA NO JUSTIFICADA'),
        ('8', '8 - S.P. POR TEMPORADA O INTERMITENTE'),
        ('12', '12 - S.P. ENFERM PADRE CONYUGE O CONVIVIENTE'),
        ],
        string="Tipo Suspención Perfecta PLAME (Ausencia)", tracking=True, )
    
    suspension_imperfecta = fields.Selection([
        ('20', '20 - S.I. ENFERM/ACCIDENTE (20 PRIMEROS DÍAS)'),
        ('21', '21 - S.I. INCAP TEMPORAL (SUBSIDIADO)'),
        ('22', '22 - S.I. MATERNIDAD - PRE Y POST NATAL'),
        ('23', '23 - S.I. DESCANSO VACACIONAL'),
        ('24', '24 - S.I. LIC DESEMP CARGO CÍVICO Y PARA SMO'),
        ('25', '25 - S.I. LIC DESEMPEÑO CARGOS SINDICALES'),
        ('26', '26 - S.I. LICENCIA CON GOCE DE HABER'),
        ('27', '27 - S.I. DÍAS COMPENS POR HORAS DE SOBRETIEMPO'),
        ('28', '28 - S.I. DÍAS LICENCIA POR PATERNIDAD'),
        ('29', '29 - S.I. DIAS LICENCIA POR ADOPCIÓN'),
        ('30', '30 - S.I. IMPOSICIÓN MEDIDA CAUTELAR'),
        ('31', '31 - S.I. CITA JUDICIAL MILITAR POLICIAL'),
        ('32', '32 - S.I. FALLEC CÓNYUGE PADRES HIJOS Y HERMANOS'),
        ('33', '33 - S.I. REPRESENT DEL ESTADO EN EVENTOS'),
        ('34', '34 - S.I. DESC VACAC LIC POR ASISTE MÉDICA O TERAP'),
        ('35', '35 - S.I. ENFERMEDAD GRAVE O TERMINAL O ACCIDENTE GRAVE'),
    ], string="Tipo de Suspensión Imperfecta PLAME (Permiso)", tracking=True, )
    
    attachment_ids = fields.Many2many(
                "ir.attachment", "zleave_permission_ir_attachment_rel", "permission_id", "attachment_id",
                string="Documentos de sustento"
)
    state = fields.Selection(
        [   ('draft', 'Borrador'),
            ('submitted', 'Enviado'),
            ('approved', 'Aprobado'),
            ('refused', 'Rechazado'),
            ('cancelled', 'Anulado'),
        ],
        string="Estado", default='draft',tracking=True, )
    
    ###############
    def _get_default_approver_user(self, employee):
        """Asignar aprobador por defecto: solo jefe directo (sin gestor de ausencias)."""
        if not employee:
            return False
        # Asignamos al jefe directo si existe
        if employee.parent_id and employee.parent_id.user_id:
            return employee.parent_id.user_id
        return False
        
    @api.onchange("employee_id")
    def _onchange_employee_id_set_approver(self):
        for rec in self:
            if rec.employee_id:
                rec.approver_id = rec._get_default_approver_user(rec.employee_id) or False
            else:
                rec.approver_id = False

    ######################################################
    #creacion del nombre
    @api.model
    def _get_or_create_permission_sequence(self):
        """Crea la secuencia si no existe (sin XML)"""
        code = "zleave.permission"
        seq = self.env["ir.sequence"].sudo().search([("code", "=", code)], limit=1)
        if not seq:
            seq = self.env["ir.sequence"].sudo().create({
                "name": "Secuencia Permisos ZLeave",
                "code": code,
                "prefix": "Permiso-",
                "padding": 4,            # Permiso-0001
                "number_next": 1,
                "number_increment": 1,
                "company_id": False,     # global
            })
        return seq

    @api.model_create_multi
    def create(self, vals_list):
        seq = self._get_or_create_permission_sequence()

        for vals in vals_list:
            # Si viene vacío o con "/" => generar
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = seq.next_by_id()

        records = super().create(vals_list)
        return records
    
    #############################
    # Método para asignar aprobador cuando se presiona el botón "Enviar"
   
    def action_send_for_approval(self):
        for rec in self:
            # Buscamos el jefe directo o responsable de RRHH
            approver = rec._get_default_approver_user(rec.employee_id)
            
            if not approver:
                raise UserError(_("No se pudo asignar un aprobador para este permiso."))

            # Asignamos el aprobador
            rec.approver_id = approver.id
            rec.state = "submitted"  # Cambiamos el estado a "Enviado"

            # Publicamos un mensaje indicando que se ha enviado para aprobación
            rec.message_post(body=_("Permiso enviado para aprobación."))
        return True
    
    ############
    def _check_is_approver(self):
        for rec in self:
            if rec.approver_id and rec.approver_id != self.env.user:
                raise UserError(_("Solo el aprobador asignado puede aprobar o rechazar este permiso."))

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Solo puedes aprobar permisos en estado Enviado."))
            rec._check_is_approver()
            rec.state = "approved"
            rec.message_post(body=_("Permiso aprobado."))
            # Cierra actividades pendientes del tipo To Do (si las creas al enviar)
            try:
                rec.activity_feedback(["mail.mail_activity_data_todo"])
            except Exception:
                pass
        return True

    def action_refuse(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Solo puedes rechazar permisos en estado Enviado."))
            rec._check_is_approver()
            rec.state = "refused"
            rec.message_post(body=_("Permiso rechazado."))
            try:
                rec.activity_feedback(["mail.mail_activity_data_todo"])
            except Exception:
                pass
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state in ("approved", "refused", "cancelled"):
                raise UserError(_("No puedes anular un permiso ya finalizado."))
            rec.state = "cancelled"
            rec.message_post(body=_("Permiso anulado."))
        return True

    ###########################################################
    @api.depends("employee_id", "type_permission", "suspension_perfecta", "suspension_imperfecta", "date_from", "date_to")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or ""
            rango = ""
            if rec.date_from and rec.date_to:
                rango = f"{rec.date_from} → {rec.date_to}"
            tipo = dict(self._fields["type_permission"].selection).get(rec.type_permission, "")
            codigo = rec.suspension_perfecta or rec.suspension_imperfecta or ""
            rec.display_name = f"{emp} - {tipo} {codigo} ({rango})"

    @api.depends("date_from", "date_to")
    def _compute_duration_days(self):
        for rec in self:
            rec.duration_days = 0.0
            if rec.date_from and rec.date_to:
                if rec.date_to < rec.date_from:
                    rec.duration_days = 0.0
                else:
                    rec.duration_days = (rec.date_to - rec.date_from).days + 1

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_("La fecha 'Hasta' no puede ser menor que 'Desde'."))

    @api.constrains("type_permission", "suspension_perfecta", "suspension_imperfecta")
    def _check_plame_code(self):
        for rec in self:
            if rec.type_permission == "sin_goce":
                if not rec.suspension_perfecta:
                    raise ValidationError(_("Si es Licencia Sin Goce / Ausencia, debes seleccionar un tipo de Suspensión Perfecta (PLAME)."))
                if rec.suspension_imperfecta:
                    raise ValidationError(_("Para Licencia Sin Goce / Ausencia no debes seleccionar Suspensión Imperfecta."))
            if rec.type_permission == "con_goce":
                if not rec.suspension_imperfecta:
                    raise ValidationError(_("Si es Licencia Con Goce / Permiso, debes seleccionar un tipo de Suspensión Imperfecta (PLAME)."))
                if rec.suspension_perfecta:
                    raise ValidationError(_("Para Licencia Con Goce / Permiso no debes seleccionar Suspensión Perfecta."))