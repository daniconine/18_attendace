from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError, AccessError
from babel import dates

class ZPeriod(models.Model):
    _name = "zperiod"
    _description = "Periodo para la Generación de Planilla"
    _inherit = ["mail.thread", "mail.activity.mixin", "hr.lock.mixin"]
    _order = "date_start desc, employee_id"

    name = fields.Char(string="Referencia", readonly=True, copy=False)
    batch_id = fields.Many2one("zperiod.batch", string="Lote de Origen", ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, tracking=True)
    company_id = fields.Many2one("res.company",string="Compañía",default=lambda self: self.env.company)
    # Heredamos las fechas del lote o se ponen manualmente
    date_start = fields.Date(string="Fecha Inicio", required=True, tracking=True)
    date_end = fields.Date(string="Fecha Fin", required=True, tracking=True)
    
    state = fields.Selection([("open", "Abierto"),
                            ("closed", "Cerrado"),
                            ("cancel", "Cancelado"),], string="Estado", default="open", tracking=True)

        
    #CAmpos de Modulos Z
    days_attended = fields.Float(string='Días Asistidos (Conforme)')
    days_unattended = fields.Float(string='Días Inasistencias (Conflicto)')
    diff_attendance_total = fields.Float(string="Exceso/Defecto (Hrs)")
    late_min_total = fields.Integer(string="Tardanzas (min)")
    permiso_late_total = fields.Integer(string="N° Permisos de Tardanza")
    
    days_vacations = fields.Float(string='Vacaciones Aprobadas (días)')
    days_permissions = fields.Float(string='Licencia con Goce Aprobadas (días)')
    days_leave_permissions = fields.Float(string='Licencia Sin Goce Aprobadas (días)')
    hrs_25 = fields.Float(string='Horas 25 %')
    hrs_35 = fields.Float(string='Horas 35 %')
    hrs_100 = fields.Float(string='Horas 100 %')
    hrs_200 = fields.Float(string='Horas 200 %')
    hrs_total = fields.Float(
        string='Horas Extras Total', 
        compute="_compute_total_hrs_extras", 
        store=True
    )
    
    # --- NUEVOS CAMPOS RELACIONALES (Esto falta) ---
    segment_line_ids = fields.One2many(
        "zperiod.segment.line", "period_id", string="Líneas de Segmentación")
    class_line_ids = fields.One2many(
        "zperiod.class.line", "period_id", string="Líneas de Clases" )
    bonus_ids = fields.One2many(
        "z.bonus", "period_id", string="Bonos" )
    commission_ids = fields.One2many(
        "z.commission", "period_id", string="Comisiones")

    # Campo técnico para la moneda de bonos/comisiones
    company_currency_id = fields.Many2one(
        'res.currency', related='batch_id.company_id.currency_id', string="Moneda")
    
    # Campo calculado para el mes
    month = fields.Selection([
        ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'), ('04', 'Abril'),
        ('05', 'Mayo'), ('06', 'Junio'), ('07', 'Julio'), ('08', 'Agosto'),
        ('09', 'Septiembre'), ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
    ], string="Mes del Periodo", compute="_compute_month", store=True, tracking=True)

    year = fields.Integer(string="Año del Periodo", compute="_compute_year", store=True)

    _sql_constraints = [('unique_employee_month_year',
                    'unique(employee_id, month, year)',
                    'Ya existe un período para este empleado en el mismo mes y año.'),]
    
    @api.depends('date_start')
    def _compute_year(self):
        for rec in self:
            rec.year = rec.date_start.year if rec.date_start else False
        
    @api.depends('date_end')
    def _compute_month(self):
        # Usamos 'self' que contiene el conjunto de registros a procesar
        for record in self: 
            if record.date_end:
                # Extraemos el mes (ej: '03')
                record.month = record.date_end.strftime('%m')
            else:
                record.month = False

    # --- Lógica de Nombre Automático ---
    @api.model
    def create(self, vals):
        if not vals.get('name'):
            emp = self.env['hr.employee'].browse(vals.get('employee_id'))

            date_end = vals.get('date_end')
            date_str = ''

            if date_end:
                date_obj = fields.Date.from_string(date_end)
                date_str = date_obj.strftime('%d-%m-%Y')

            vals['name'] = f"Periodo/{emp.name}/{date_str}"

        return super(ZPeriod, self).create(vals)

   

    def action_cancel(self):
        self.write({'state': 'cancel'})
        
    #suma de horas extras
    @api.depends('hrs_25', 'hrs_35', 'hrs_100', 'hrs_200')
    def _compute_total_hrs_extras(self):
        for record in self:
            record.hrs_total = record.hrs_25 + record.hrs_35 + record.hrs_100 + record.hrs_200
            
    #coorazon del calculo apra el resumen de contorl de asustencia        
    def action_actualizar(self):
        for period in self:
            # Validamos que tengamos los datos necesarios
            if not period.employee_id or not period.date_start or not period.date_end:
                continue

            # Buscamos los registros de asistencia en el rango de fechas
            attendance_days = self.env['zattendance.day'].search([
                ('employee_id', '=', period.employee_id.id),
                ('date', '>=', period.date_start),
                ('date', '<=', period.date_end),
            ])

            # Cálculos de conteo y sumas
            # 1. Días Asistidos (Estado Conforme)
            dias_conforme = len(attendance_days.filtered(lambda x: x.state == 'conforme'))
            
            # 2. Inasistencias (Estado Conflicto)
            dias_conflicto = len(attendance_days.filtered(lambda x: x.state == 'conflicto'))

            # 3. Sumar minutos de tardanza y permisos
            total_tardanza = sum(attendance_days.mapped('late_min'))
            total_permisos = len(attendance_days.filtered(lambda x: x.permiso_late))

            # 4. Diferencia de horas (Exceso/Defecto)
            
            diferencia_horas = sum(attendance_days.mapped('diff_attendance'))
            
            # 5. Vacaciones Aprobadas (Sumamos las vacaciones aprobadas en el periodo)
            vacations_approved = self.env['zleave.zvacation'].search([
                ('employee_id', '=', period.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '>=', period.date_start),
                ('date_to', '<=', period.date_end),
            ])
            dias_vacaciones = sum(vacations_approved.mapped('duration_days'))
            
            # 6. Permisos con goce aprobados
            permissions_approved = self.env['zleave.permission'].search([
                ('employee_id', '=', period.employee_id.id),
                ('state', '=', 'approved'),
                ('type_permission', '=', 'imperfecta'),
                ('date_from', '>=', period.date_start),
                ('date_to', '<=', period.date_end),
            ])
            dias_permisos = sum(permissions_approved.mapped('duration_days'))


            # 7. Licencias sin goce / ausencias aprobadas
            permissions_leave_approved = self.env['zleave.permission'].search([
                ('employee_id', '=', period.employee_id.id),
                ('state', '=', 'approved'),
                ('type_permission', '=', 'perfecta'),
                ('date_from', '>=', period.date_start),
                ('date_to', '<=', period.date_end),
            ])
            dias_leave_permissions = sum(permissions_leave_approved.mapped('duration_days'))
            
            # 8 Buscamos los registros de horas extras solicitadas para el empleado en el período de fechas
            overtime_records = self.env['zleave.overtime'].search([
                ('employee_id', '=', period.employee_id.id),
                ('zattendance_date', '>=', period.date_start),
                ('zattendance_date', '<=', period.date_end),
                ('state', '=', 'approved'),  # Solo consideramos las solicitudes aprobadas
            ])

            # Inicializamos las variables para acumular las horas extras
            total_hrs_25 = 0
            total_hrs_35 = 0
            total_hrs_100 = 0
            total_hrs_200 = 0

            # Sumar las horas extras de cada registro de solicitud
            for overtime in overtime_records:
                total_hrs_25 += overtime.horas_25
                total_hrs_35 += overtime.horas_35
                total_hrs_100 += overtime.horas_100
                total_hrs_200 += overtime.horas_200


            # Asignación de valores a los campos del periodo
            period.write({
                'days_attended': dias_conforme,
                'days_unattended': dias_conflicto,
                'late_min_total': total_tardanza,
                'permiso_late_total': total_permisos,
                'diff_attendance_total': diferencia_horas,
                'days_vacations': dias_vacaciones,
                'days_permissions': dias_permisos,
                'days_leave_permissions': dias_leave_permissions,
                'hrs_25': total_hrs_25,
                'hrs_35': total_hrs_35,
                'hrs_100': total_hrs_100,
                'hrs_200': total_hrs_200,
            })
        
        return True   

   
    ######Bloqueador
    is_locked = fields.Boolean(
        string="Bloqueado",
        compute="_compute_is_locked",
        store=True,
        readonly=False,
        tracking=True
    )

    @api.depends("state")
    def _compute_is_locked(self):
        for rec in self:
            rec.is_locked = rec.state in ("closed", "cancel")   
            
    #eacritura
    def write(self, vals):
        for rec in self:
            if rec.is_locked:
                raise UserError(_(
                    "Este periodo está bloqueado. No se puede modificar porque está cerrado o cancelado."
                ))

        return super(ZPeriod, self).write(vals)
    
    
    ####### CRon
    @api.model
    def cron_actualizar_periodos_abiertos(self):
        periods = self.sudo().search([
            ("state", "=", "open"),
        ])

        if periods:
            periods.with_context(
                tracking_disable=True,
                mail_notrack=True,
            ).action_actualizar()

        return True 