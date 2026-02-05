# models/zvacation.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ZVacation(models.Model):
    _name = 'zleave.zvacation'
    _description = 'Solicitud de Vacaciones'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "name"
    
    
    name = fields.Char(string="Código", copy=False, readonly=True, tracking=True)
    display_name = fields.Char(compute="_compute_display_name", store=False)
    description = fields.Text(string="Descripción o Motivo")
    company_id = fields.Many2one("res.company", string="Compañía",
                                 default=lambda self: self.env.company, required=True, readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, tracking=True)
    employee_job = fields.Many2one(related='employee_id.job_id', string="Cargo del Empl.", readonly=True)
    employee_department_id = fields.Many2one(related='employee_id.department_id', string="Departamento", readonly=True)
    requested_by_id = fields.Many2one("res.users", string="Solicitado por",
                                      default=lambda self: self.env.user, readonly=True, tracking=True)

    approver_id = fields.Many2one("res.users", string="Aprobador(a)", tracking=True, readonly=True,
                                  domain="[('share','=',False), ('company_ids','in', company_id)]",
                                  help="Por defecto: jefe directo.")
    approver_signature = fields.Binary("Firma del Aprobador(a)", attachment=True)
    hr_responsible_id = fields.Many2one('hr.employee', string="Encargado de RRHH")
    cargo_id = fields.Many2one(related='employee_id.parent_id.job_id', string="Cargo", readonly=True)
       

    date_from = fields.Date(string="Desde", required=True, tracking=True)
    date_to = fields.Date(string="Hasta", required=True, tracking=True)

    duration_days = fields.Float(string="N° Días", compute="_compute_duration_days", store=True)

    vacation_type = fields.Selection([
        ('regular', 'Vacaciones Regulares'),
        ('advance', 'Vacaciones Adelantadas'),
    ], string="Tipo de Vacaciones", default='regular', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Enviado'),
        ('approved', 'Aprobado'),
        ('refused', 'Rechazado'),
        ('cancelled', 'Anulado'),
    ], string="Estado", default='draft', tracking=True)

    allocation_ids = fields.One2many('zleave.zvacation.allocate.year', 'vacation_id', string='Asignación por Años')

    zattendance_ids = fields.One2many("zattendance.day", "vacation_id",
                        string="Registros de Asistencia", readonly=True,)
    
    approver_image_1920 = fields.Image( string="Firmado por:", related="approver_id.image_1920",
                            readonly=True,)     
    
    #############################
    # Creación de nombre secuencial (similar a lo que tienes en ZleavePermission)
    @api.model
    def _get_or_create_vacation_sequence(self):
        """Crea la secuencia si no existe (sin XML)"""
        code = "zleave.vacation"
        seq = self.env["ir.sequence"].sudo().search([("code", "=", code)], limit=1)
        if not seq:
            seq = self.env["ir.sequence"].sudo().create({
                "name": "Secuencia Vacaciones ZLeave",
                "code": code,
                "prefix": "Vacation-",
                "padding": 4,  # Vac-0001
                "number_next": 1,
                "number_increment": 1,
                "company_id": False,  # Global
            })
        return seq

    ####No ediciond espues de creado
    def write(self, vals):
        for rec in self:
            if rec.state != 'draft':
                blocked = {'employee_id','date_from','date_to','vacation_type'}
                if any(field in vals for field in blocked):
                    raise UserError("No puede modificar la solicitud después de ser creada. Debe anular y generar una nueva.")
        return super().write(vals)
        
    #############################
    @api.model_create_multi
    def create(self, vals_list):
        seq = self._get_or_create_vacation_sequence()
        records = self.env['zleave.zvacation']   # <-- recordset vacío

        for vals in vals_list:

            # Validación: solo una solicitud en borrador
            if vals.get("employee_id"):
                existing = self.env['zleave.zvacation'].search([
                    ('employee_id', '=', vals['employee_id']),
                    ('state', '=', 'draft')
                ], limit=1)
                if existing:
                    raise UserError(
                        "El empleado ya tiene una solicitud en BORRADOR."
                    )

            # Secuencia
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = seq.next_by_id()

            # Aprobador
            if not vals.get("approver_id") and vals.get("employee_id"):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                approver = self._get_default_approver_user(employee)
                if approver:
                    vals["approver_id"] = approver.id

            # Crear registro
            record = super(ZVacation, self).create(vals)

            # → Agregar al recordset, NO a lista
            records |= record

            # FIFO mapeo
            self.env['zleave.zvacation.allocate.year'].allocate_days_for_vacation(record)

        return records



    #############################
    # Cálculo de duración de las vacaciones en días
    @api.depends("date_from", "date_to")
    def _compute_duration_days(self):
        for rec in self:
            rec.duration_days = 0.0
            if rec.date_from and rec.date_to:
                if rec.date_to < rec.date_from:
                    rec.duration_days = 0.0
                else:
                    rec.duration_days = (rec.date_to - rec.date_from).days + 1

    
    @api.model
    def _get_default_approver_user(self, employee):
        """Asignar aprobador por defecto: solo jefe directo (sin gestor de vacaciones)."""
        if not employee:
            return False
        # Asignamos al jefe directo si existe
        if employee.parent_id and employee.parent_id.user_id:
            return employee.parent_id.user_id
        return False

    #############################
    # Generación del nombre
    @api.depends("employee_id", "date_from", "date_to")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or ""
            rango = f"{rec.date_from} → {rec.date_to}" if rec.date_from and rec.date_to else ""
            rec.display_name = f"{emp} - {rango}"
            
    
    ################################Logica de Enviar y  Aprobacion######
    #############################
    # Verificación del aprobador
    def _check_is_approver(self):
        for rec in self:
            if rec.approver_id and rec.approver_id != self.env.user:
                raise UserError(_("Solo el aprobador asignado puede aprobar o rechazar esta solicitud."))

    def action_send_for_approval(self):
        """Enviar para aprobación"""
        for rec in self:
           
            # Asignar el aprobador por defecto si no está asignado
            approver = rec._get_default_approver_user(rec.employee_id)
            if not approver:
                raise UserError(_("No se pudo asignar un aprobador para esta solicitud."))
            
            rec.approver_id = approver.id
            rec.state = 'submitted'  # Cambiar el estado a "Enviado"
            
            # Publicamos un mensaje indicando que se ha enviado para aprobación
            rec.message_post(body=_("Solicitud de Vacaciones esta siendo enviado . . . . . "))
            
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
            template = self.env.ref('zleave.email_template_zleave_vacation')  # Asegúrate de que el ID de la plantilla sea correcto
            
            if template:
                # Usamos el correo del aprobador en el campo "email_to" y ponemos en "CC" al empleado y al encargado de RRHH
                template.write({
                    'email_to': approver_email,
                    'email_cc': f"{employee_email},{hr_email}"
                })
                # Enviar el correo
                template.send_mail(rec.id, force_send=True)
            
            rec.message_post(body=_("Solicitud ha sido enviado a los correos: " + email_message))
              
            # Puedes agregar la lógica para el envío de correos electrónicos o cualquier otra acción aquí
        return True
    
   

    #############################
    # Generación de las líneas de asignación
    def _create_allocation_lines(self):
        """Este método genera las líneas de asignación para cada año de vacaciones."""
        for vacation in self:
            # Calcular los días asignados para cada año
            vacation_years = self.env['zleave.zvacation.year'].search([
                ('employee_id', '=', vacation.employee_id.id)
            ])
            for year in vacation_years:
                allocated_days = vacation.duration_days  # Lógica de distribución de días
                self.env['zleave.zvacation.allocate.year'].create({
                    'vacation_id': vacation.id,
                    'vacation_year_id': year.id,
                    'days_allocated': allocated_days,
                })

  
     #############################
    # Aprobación
    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Solo puedes aprobar solicitudes de vacaciones en estado Enviado."))
            
            rec._check_is_approver()
            
            # 1) Asegurar días de asistencia en el rango
            created, _updated = self.env["zattendance.day"].ensure_days(
                rec.employee_id, rec.date_from, rec.date_to
            )
            if created:
                rec.message_post(
                    body=_("Se generaron %s registros de asistencia para aplicar las vacaciones.") % created
                )

            # 2) Buscar días y aplicar vacaciones
            attendance_days = self.env["zattendance.day"].search([
                ("employee_id", "=", rec.employee_id.id),
                ("date", ">=", rec.date_from),
                ("date", "<=", rec.date_to),
            ])
            if not attendance_days:
                raise UserError(_("No fue posible generar registros de asistencia para este rango de fechas."))

            for att in attendance_days:
                att.vacaciones(rec.id)
            
            rec.state = "approved"
            rec.message_post(body=_("Vacaciones aprobadas."))

            # 4) Cerrar actividades pendientes
            try:
                rec.activity_feedback(["mail.mail_activity_data_todo"])
            except Exception:
                pass
                

        return True   
        
        
    #############################
    # Rechazo
    def action_refuse(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Solo puedes rechazar solicitudes de vacaciones en estado Enviado."))
            rec._check_is_approver()
            rec.state = "refused"
            rec.message_post(body=_("Vacaciones rechazadas."))

        return True

    #############################
    # Cancelación
    def action_cancel(self):
        for rec in self:
            if rec.state in ("approved", "refused", "cancelled"):
                raise UserError(_("No puedes anular una solicitud ya finalizada."))
            rec.state = "cancelled"
            rec.message_post(body=_("Vacaciones anuladas."))

        return True

    
    ################################### 
    # Campo calculado para traer todos los registros de vacation_year asociados al empleado
    vacation_year_ids = fields.One2many(
        'zleave.zvacation.year', 
        'vacation_id', 
        string="Años de Vacaciones", 
        compute='_compute_vacation_years', 
        store=True
    )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Cuando se selecciona un empleado, trae todos los años de vacaciones relacionados con él"""
        for rec in self:
            if rec.employee_id:
                # Traemos todos los registros de vacation_year para el empleado seleccionado
                vacation_years = self.env['zleave.zvacation.year'].search([
                    ('employee_id', '=', rec.employee_id.id)
                ])
                # Asignamos los registros de vacation_year_id al campo vacation_year_ids
                rec.vacation_year_ids = [(6, 0, vacation_years.ids)]
            else:
                rec.vacation_year_ids = [(5, 0, 0)]  # Limpiamos el campo si no hay empleado seleccionado

    @api.depends('employee_id')
    def _compute_vacation_years(self):
        """Este método se asegura de que siempre que se seleccione un empleado, los años de vacaciones se traigan correctamente"""
        for vacation in self:
            if vacation.employee_id:
                vacation_years = self.env['zleave.zvacation.year'].search([
                    ('employee_id', '=', vacation.employee_id.id)
                ])
                vacation.vacation_year_ids = [(6, 0, vacation_years.ids)]
            else:
                vacation.vacation_year_ids = [(5, 0, 0)]  #
    
        
     
    
    
    
    
    
    
    
    
   
 
    #Mapeo de registros de zvacation_year
    @api.depends('allocation_ids')
    def _compute_vacation_years(self):
        for vacation in self:
            # Usamos 'mapped' para traer los registros de vacation_year_id desde la tabla intermedia
            vacation_years = vacation.allocation_ids.mapped('vacation_year_id')
            vacation.vacation_year_ids = [(6, 0, vacation_years.ids)]