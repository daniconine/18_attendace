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
    ], string="Estado de Asistencia", related='zattendance_id.state',readonly=True)
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
    horas_100 = fields.Float(string="Horas 100%")
    horas_200 = fields.Float(string="Horas 200%")
    
    # Estado de la solicitud
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Enviado'),
        ('approved', 'Aprobado'),
        ('refused', 'Rechazado'),
        ('cancelled', 'Anulado'),
    ], string="Estado", default='draft', tracking=True)

    analytic_account_id = fields.Many2one("account.analytic.account", string="Cuenta Analítica (CCA)", required=True)

    approver_image_1920 = fields.Image( string="Firmado por:", related="approver_id.image_1920",
                            readonly=True,)
    employee_department_id = fields.Many2one(related='employee_id.department_id', string="Departamento", readonly=True)
    cargo_id = fields.Many2one(related='employee_id.parent_id.job_id', string="Cargo", readonly=True)
    name_id = fields.Many2one(related='employee_id.parent_id', string="Nombre", readonly=True)
   

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
            # Verificación de zattendance_id (debe estar presente)
            if not vals.get('zattendance_id'):
                raise UserError(_("Debe seleccionar un registro de asistencia para la solicitud de horas extras."))

            # Obtener el registro de asistencia (ZAttendance)
            zattendance = self.env['zattendance.day'].browse(vals['zattendance_id'])
            
            # Verificación del estado de la asistencia (debe ser "conforme")
            if zattendance.state != 'conforme':
                raise UserError(_("El estado de la asistencia debe ser 'Conforme' para crear la solicitud de horas extras."))

            # Verificación de que la diferencia de horas sea mayor que 0
            if zattendance.diff_attendance <= 0:
                raise UserError(_("La diferencia de horas debe ser mayor a 0 para poder solicitar horas extras."))

            # Verificación de las horas solicitadas (deben ser menores que las horas en exceso)
            total_hours_requested = vals.get('total_hours_requested')  # Acceder al valor de las horas solicitadas desde 'vals'
            
            if total_hours_requested and total_hours_requested > zattendance.diff_attendance:
                raise UserError(_("Las horas extras solicitadas deben ser menores o iguales al exceso de horas registrado."))

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
    
    ######Metodo para el caluclo de horas
    def _calculate_overtime_hours(self, total_hours_requested, zattendance_type):
        """
        Calcula la distribución de horas extras según el tipo de asistencia.
        :param total_hours_requested: Total de horas solicitadas por el empleado.
        :param zattendance_type: Tipo de asistencia ('presencial', 'virtual', 'descanso', 'feriado')
        :return: Diccionario con la distribución de las horas (horas_25, horas_35, horas_100, horas_200)
        """
        horas_25 = 0.0
        horas_35 = 0.0
        horas_100 = 0.0
        horas_200 = 0.0

        if zattendance_type in ['presencial', 'virtual']:
            # Para presencia o virtual, las primeras 2 horas son al 25% y el resto al 35%
            horas_25 = min(2, total_hours_requested)  # Hasta 2 horas al 25%
            horas_35 = total_hours_requested - horas_25  # El resto va al 35%
        
        elif zattendance_type == 'descanso':
            # Para descanso, siempre asignamos 8 horas al 100%
            horas_100 = 8  # Máximo 8 horas al 100%
        
        elif zattendance_type == 'feriado':
            # Para feriado, siempre asignamos 8 horas al 200%
            horas_200 = 8  # Máximo 8 horas al 200%
        
        return {
            'horas_25': horas_25,
            'horas_35': horas_35,
            'horas_100': horas_100,
            'horas_200': horas_200
        }
              
    #######Envio de solicitud
    def action_send_for_approval(self):
        for rec in self:
            # Verificamos si el aprobador está asignado
            if not rec.approver_id:
                raise UserError(_("Debe asignar un aprobador antes de enviar la solicitud."))

            # Calcular las horas extras según el tipo de asistencia
            calculated_hours = self._calculate_overtime_hours(rec.total_hours_requested, rec.zattendance_type)
            
            # Asignar las horas calculadas a los campos correspondientes
            rec.horas_25 = calculated_hours['horas_25']
            rec.horas_35 = calculated_hours['horas_35']
            rec.horas_100 = calculated_hours['horas_100']
            rec.horas_200 = calculated_hours['horas_200']

            # Cambiar el estado a "Enviado"
            rec.state = "submitted"  # Cambiamos el estado a "Enviado"

            # Publicamos un mensaje indicando que se ha enviado para aprobación
            rec.message_post(body=_("La solicitud está siendo enviada para su aprobación..."))
            
            # Obtener los correos electrónicos
            approver_email = rec.approver_id.email or False  # Correo del aprobador
            employee_email = rec.employee_id.work_email or False  # Correo del empleado
            hr_email = "jbernui@gerens.pe, pmanrique@gerens.pe"  # Correo de RRHH
            
            # Construir el mensaje con los correos electrónicos
            email_message = f"Aprobador: {approver_email or 'No disponible'}, "
            email_message += f"Empleado: {employee_email or 'No disponible'}, "
            email_message += f"RRHH: {hr_email or 'No disponible'}"
            
            # Enviar el correo de notificación
            template = self.env.ref('zleave.email_template_zleave_overtime')  # Asegúrate de que el ID de la plantilla sea correcto
            
            if template:
                # Usamos el correo del aprobador en el campo "email_to" y ponemos en "CC" al empleado y al encargado de RRHH
                template.write({
                    'email_to': approver_email,
                    'email_cc': f"{employee_email},{hr_email}"
                })
                # Enviar el correo
                template.send_mail(rec.id, force_send=True)
            
            # Mensaje final indicando que la solicitud fue enviada
            rec.message_post(body=_("La solicitud de horas extras ha sido enviada a los correos: " + email_message))

        return True
    
    ###Aprobacion
    def _check_is_approver(self):
        for rec in self:
            if rec.approver_id and rec.approver_id != self.env.user:
                raise UserError(_("Solo el aprobador asignado puede aprobar o rechazar este permiso."))

    
    def action_approve(self):
        for rec in self:
            # Verificación de que el estado es "Enviado"
            if rec.state != "submitted":
                raise UserError(_("Solo puedes aprobar permisos en estado 'Enviado'."))

            # Verificación de si el usuario es el aprobador asignado
            rec._check_is_approver()
          
            # Cambiar el estado a "Aprobado"
            rec.state = "approved"
            
            # Publicar un mensaje indicando que la solicitud ha sido aprobada
            rec.message_post(body=_("Solicitud de Hora Extra aprobada."))

            # 3) Cerrar actividades pendientes (si las hubiera)
            try:
                rec.activity_feedback(["mail.mail_activity_data_todo"])
            except Exception:
                pass

        return True
    
    def action_refuse(self):
        for rec in self:
            # Verificación de estado (solo puede rechazarse si está en estado 'Enviado')
            if rec.state != "submitted":
                raise UserError(_("Solo puedes rechazar permisos en estado 'Enviado'."))

            # Verificamos que el usuario que intenta rechazar sea el aprobador
            rec._check_is_approver()

            # Cambiar estado a 'Rechazado'
            rec.state = "refused"
            
            # Publicamos un mensaje indicando que la solicitud ha sido rechazada
            rec.message_post(body=_("Solicitud de horas extras rechazada por el aprobador."))
            
            # Cerrar actividades pendientes (si las hubiera)
            try:
                rec.activity_feedback(["mail.mail_activity_data_todo"])
            except Exception:
                pass
        
        return True

    def action_cancel(self):
        for rec in self:
            # Verificamos que no esté ya en un estado final (aprobado, rechazado, anulado)
            if rec.state in ("approved", "refused", "cancelled"):
                raise UserError(_("No puedes anular un permiso que ya ha sido aprobado, rechazado o anulado."))

            # Cambiar el estado a 'Anulado'
            rec.state = "cancelled"
            
            # Publicamos un mensaje indicando que la solicitud ha sido anulada
            rec.message_post(body=_("Solicitud de horas extras anulada por el usuario."))
        
        return True