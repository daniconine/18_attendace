# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
from odoo.http import request

_logger = logging.getLogger(__name__)

class ZleavePermission(models.Model):
    _name = "zleave.permission"
    _description = "ZleavePermission - Solicitud Licencia"
    _inherit = ["mail.thread", "mail.activity.mixin", "hr.lock.mixin"]
    _order = "create_date desc"
    _rec_name = "name" 
    
    
    name = fields.Char( string="Código",copy=False,readonly=True,tracking=True,)
    display_name = fields.Char(compute="_compute_display_name", store=False)
    description = fields.Text(string="Descripción o Motivo", required=True)
    company_id = fields.Many2one("res.company", string="Compañía",
                default=lambda self: self.env.company,required=True, readonly=True,)
    employee_id = fields.Many2one("hr.employee",string="Empleado",required=True,     
                    tracking=True,)
    employee_job = fields.Many2one(related='employee_id.job_id', string="Cargo del Empl.", readonly=True,)
    employee_department_id = fields.Many2one(related='employee_id.department_id', string="Departamento", readonly=True)
    cargo_id = fields.Many2one(related='employee_id.parent_id.job_id', string="Cargo", readonly=True)
    name_id = fields.Many2one(related='employee_id.parent_id', string="Nombre", readonly=True)
   


    requested_by_id = fields.Many2one( "res.users", string="Solicitado por",
                    default=lambda self: self.env.user,readonly=True, tracking=True,)

    approver_id = fields.Many2one("res.users", string="Aprobador(a)", tracking=True, readonly=True,
        domain="[('share','=',False), ('company_ids','in', company_id)]",
        help="Por defecto: employee.leave_manager_id (Aprobador de Solicitud de Licencia) y fallback a jefe directo.",
    )
   
    hr_responsible_id = fields.Many2one('hr.employee', string="Encargado de RRHH")  # Asumiendo que tienes un campo para RRHH

    date_from = fields.Date(string="Desde", required=True, tracking=True)
    date_to = fields.Date(string="Hasta", required=True, tracking=True)
    
    duration_days = fields.Float(string="Solicitado (días)", compute="_compute_duration_days", store=True)

    type_permission = fields.Selection(
        [   ('perfecta', 'Licencia Sin Goce (S.P.)/Ausencia'),
            ('imperfecta', 'Licencia Con Goce (S.I)/Permiso'),            
        ],
        string="Tipo de Licencia", required=True, tracking=True, )
    
    suspension_id = fields.Many2one('zlabor.suspension.code',string="Código de Suspensión Laboral",
                        required=True,tracking=True,)
        
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
    
    approver_image_1920 = fields.Image( string="Firmado por:", related="approver_id.image_1920",
                            readonly=True,)         
    #######################       
    #ction_id
    # Campo computado para almacenar el ID de la acción
    # Campo para almacenar el ID de la acción
    action_url = fields.Char(string="URL de Aprobación", compute='get_action_url', store=False)

    def get_action_url(self):
        """
        Obtiene dinámicamente el ID de la acción asociada al modelo zleave.permission y lo almacena en el campo action_url.
        """
        # Buscar la acción asociada al modelo zleave.permission             
        action = self.env['ir.actions.act_window'].sudo().search([
            ('res_model', '=', 'zleave.overtime')], limit=1)


        # Si se encuentra la acción, construimos la URL con el ID de la acción y el ID del registro
        if action:
            self.action_url = f"https://erp.gerens.pe/odoo/action-{action.id}/{self.id}"
        else:
            self.action_url = "Acción no encontrada"
        
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
                "prefix": "Licencia-",
                "padding": 4,            # Licencia-0001
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
                raise UserError("Debe adjuntar al menos un archivo antes de guardar la solicitudde licencia.")


            # Buscamos el jefe directo o responsable de RRHH
            approver = rec._get_default_approver_user(rec.employee_id)
            
            if not approver:
                raise UserError(_("No se pudo asignar un aprobador para este permiso."))

            # Asignamos el aprobador
            rec.approver_id = approver.id
            rec.state = "submitted"  # Cambiamos el estado a "Enviado"
            
            # Publicamos un mensaje indicando que se ha enviado para aprobación
            rec.message_post(body=_("Solicitud de licencia esta siendo enviado . . . . . "))
            
            # Obtener los correos electrónicos
            approver_email = approver.email or False  # Correo del aprobador
            employee_email = rec.employee_id.work_email or False  # Correo del empleado
            #hr_email = rec.hr_responsible_id.work_email or False  # Correo del encargado de RRHH
            hr_email = "jbernui@gerens.pe, agente.rrhh@gerens.pe"
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
            
            rec.message_post(body=_("Solicitud de Licencia ha sido enviado a los correos: " + email_message))
               
        return True

    ##############
   
    def _check_is_approver(self):
        for rec in self:
            if rec.approver_id and rec.approver_id != self.env.user:
                raise UserError(_("Solo el aprobador asignado puede aprobar o rechazar esta licencia."))

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Solo puedes aprobar licencias en estado Enviado."))
            
            rec._check_is_approver()
            rec.state = "approved"
            rec.message_post(body=_("Solicitud de licencia aprobado."))
            
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
                raise UserError(_("Solo puedes rechazar solicitudes en estado Enviado."))
            rec._check_is_approver()
            rec.state = "refused"
            rec.message_post(body=_("Solicitud de licencia rechazado."))
            
            try:
                rec.activity_feedback(["mail.mail_activity_data_todo"])
            except Exception:
                pass
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state in ("approved", "refused", "cancelled"):
                raise UserError(_("No puedes anular una solicitud ya finalizado."))
            rec.state = "cancelled"
            rec.message_post(body=_("Solicitud de licencia anulado."))
        return True

    ###########################################################
    ### Suspencion Perfecta e imperfecta de acuerdo al tipo seleccionado
    @api.depends("employee_id", "type_permission", "suspension_id", "date_from", "date_to")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or ""
            rango = ""
            if rec.date_from and rec.date_to:
                rango = f"{rec.date_from} → {rec.date_to}"
            tipo = dict(self._fields["type_permission"].selection).get(rec.type_permission, "")          
            codigo = ""
            if rec.suspension_id:
                codigo = f"{rec.suspension_id.code} - {rec.suspension_id.name}"

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
    
  
    #######################
    # Le decimos que ahora depende del estado para marcarse solo
    is_locked = fields.Boolean(string="Bloqueado",
        compute="_compute_is_locked", 
        store=True, 
        readonly=False,
        tracking=True
    )

    @api.depends('state')
    def _compute_is_locked(self):
        for rec in self:
            # Lógica: Si es borrador está abierto, cualquier otro estado bloquea
            rec.is_locked = rec.state != 'draft'

    # El permiso de RRHH para abrir el candado manualmente
    def _check_lock_permission(self):
        res = super(ZleavePermission, self)._check_lock_permission()
        return res or self.env.user.has_group('zleave.group_hr_manager')   