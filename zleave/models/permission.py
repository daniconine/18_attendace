# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
from odoo.http import request

_logger = logging.getLogger(__name__)

class ZleavePermission(models.Model):
    _name = "zleave.permission"
    _description = "ZleavePErmission - Permisos"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "name" 

    
    name = fields.Char( string="Código",copy=False,readonly=True,tracking=True,)
    display_name = fields.Char(compute="_compute_display_name", store=False)
    description = fields.Text(string="Descripción o Motivo")
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
    hr_responsible_id = fields.Many2one('hr.employee', string="Encargado de RRHH")  # Asumiendo que tienes un campo para RRHH

    date_from = fields.Date(string="Desde", required=True, tracking=True)
    date_to = fields.Date(string="Hasta", required=True, tracking=True)
    
    duration_days = fields.Float(string="Solicitado (días)", compute="_compute_duration_days", store=True)

    type_permission = fields.Selection(
        [   ('lic_sin_goce', 'Licencia Sin Goce (S.P.)/Ausencia'),
            ('lic_con_goce', 'Licencia Con Goce (S.I)/Permiso'),            
        ],
        string="Ausencia/Permiso", required=True, tracking=True, )
    
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
    
    state = fields.Selection(
        [   ('draft', 'Borrador'),
            ('submitted', 'Enviado'),
            ('approved', 'Aprobado'),
            ('refused', 'Rechazado'),
            ('cancelled', 'Anulado'),
        ],
        string="Estado", default='draft',tracking=True, )
    
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'zleave_permission_attachment_rel', 
        'zleave_permission_id', 
        'attachment_id', 
        string="Archivos Adjuntos"
    )
    zattendance_ids = fields.One2many('zattendance.day', 'permission_id', 
                                      string="Registros de Asistencia")
    #######################
    #Busca el URL para enviar el correo
    #Revisar si funciona en entorno con dominio, si no reemplazar en plantilla la url dle sistema
    def get_permission_approval_url(self):
        """
        Genera una URL para que el aprobador pueda revisar y aprobar la solicitud de permiso.
        """
        # Obtener la URL base del sistema
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if base_url:
            return f"{base_url}/web#id={self.id}&view_type=form&model=zleave.permission"
        else:
            # Si no se encuentra la URL base, devuelve un mensaje de error o una URL por defecto
            return "URL no configurada correctamente"
    #######################
    # Método para abrir los documentos adjuntos
    def action_open_documents(self):
        return {
            'name': _('Documents of Permission'),
            'view_type': 'form',
            'view_mode': 'kanban,list,form',
            'res_model': 'ir.attachment',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('res_model', '=', 'zleave.permission'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'zleave.permission', 'default_res_id': self.id},
        }
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
        # Crear la secuencia de permisos si no existe
        seq = self._get_or_create_permission_sequence()

        for vals in vals_list:
            # Si no viene con un nombre, generamos uno con la secuencia
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = seq.next_by_id()

            # Asignar el aprobador por defecto si no se ha asignado
            if not vals.get("approver_id") and vals.get("employee_id"):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                approver = self._get_default_approver_user(employee)
                if approver:
                    vals["approver_id"] = approver.id

        # Crear los registros
        records = super(ZleavePermission, self).create(vals_list)
        return records
    
    #############################
   
    def action_send_for_approval(self):
           
        for rec in self:
            # Verificamos si el permiso tiene archivos adjuntos
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'zleave.permission'),
                ('res_id', '=', rec.id)
            ])
            
            if not attachments:  # Si no hay archivos adjuntos
                raise UserError("Debe adjuntar al menos un archivo antes de guardar la solicitud.")


            # Buscamos el jefe directo o responsable de RRHH
            approver = rec._get_default_approver_user(rec.employee_id)
            
            if not approver:
                raise UserError(_("No se pudo asignar un aprobador para este permiso."))

            # Asignamos el aprobador
            rec.approver_id = approver.id
            rec.state = "submitted"  # Cambiamos el estado a "Enviado"

            # Publicamos un mensaje indicando que se ha enviado para aprobación
            rec.message_post(body=_("Permiso esta siendo enviado . . . . . "))
            
            # Obtener los correos electrónicos
            approver_email = approver.email or False  # Correo del aprobador
            employee_email = rec.employee_id.work_email or False  # Correo del empleado
            #hr_email = rec.hr_responsible_id.work_email or False  # Correo del encargado de RRHH
            hr_email = "jbernui@gerens.pe, pmanrique@gerens.pe"
            # Construir el mensaje con los correos electrónicos
            email_message = "Aprobador: " + (approver_email or "No disponible") + ", "
            email_message += "Empleado: " + (employee_email or "No disponible") + ", "
            email_message += "RRHH: " + (hr_email or "No disponible")
                
            # Enviar el correo de notificación
            template = self.env.ref('zleave.email_template_zleave_permission')  # Asegúrate de que el ID de la plantilla sea correcto
            
            if template:
                # Usamos el correo del aprobador en el campo "email_to" y ponemos en "CC" al empleado y al encargado de RRHH
                template.write({
                    'email_to': approver_email,
                    'email_cc': f"{employee_email},{hr_email}"
                })
                # Enviar el correo
                template.send_mail(rec.id, force_send=True)
            
            rec.message_post(body=_("Permiso ha sido enviado a los correos: " + email_message))
               
        return True

    ##############
   
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
            
             # 1) Asegurar que existan días de asistencia en el rango
            created, _updated = self.env['zattendance.day'].ensure_days(
                rec.employee_id, rec.date_from, rec.date_to
            )
            if created:
                rec.message_post(body=_("Se generaron %s registros de asistencia para aplicar el permiso.") % created)

            # 2) Buscar días y aplicar permiso
            attendance_day = self.env['zattendance.day'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
            ])

            if not attendance_day:
                # Esto ya sería raro porque ensure_days los crea
                raise UserError(_("No fue posible generar registros de asistencia para este rango de fechas."))

            for att in attendance_day:
                att.permiso(rec.id)

            # 3) Cerrar actividades pendientes
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