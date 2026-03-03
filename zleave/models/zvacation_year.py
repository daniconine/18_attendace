######################
####### MODLEO DE ACUMUALCION DE VACACIONES

from odoo import models, fields, api
from datetime import datetime
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError, ValidationError


class ZVacationYear(models.Model):
    _name = 'zleave.zvacation.year'
    _description = 'Acumulación de Vacaciones Anual'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "display_name"

    company_id = fields.Many2one("res.company", string="Compañía",
                                 default=lambda self: self.env.company, required=True, readonly=True)
    
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    
    year = fields.Char(string='Año Periodo',store=True,compute='_compute_period_data',readonly=True)
    start_date = fields.Date(string='Fecha inicial Acumulación', default=fields.Date.today)
    end_date = fields.Date(string='Fecha final Acumulación' )
    accumulated_days = fields.Float(string='Días Acumulados')
    consumed_days = fields.Float(string='Días Consumidos Totales', compute='_compute_consumed', store=True)
    balance_days = fields.Float(string='Saldo',compute='_compute_balance', store=True)
    
    consumed_days_manual = fields.Float(string='Días Consumidos Manuales')
    
    # Relación con la tabla puente
    allocation_ids = fields.One2many('zleave.zvacation.allocate.year',
        'vacation_year_id', string='Vacaciones Asignadas' )
    vacation_id = fields.Many2one('zleave.zvacation', string='Solicitud de Vacaciones', ondelete='cascade')
    
    display_name = fields.Char( string="Nombre",compute='_compute_display_name' ,
                            store=True )
          
    state = fields.Selection([
        ('accrual', 'Acumulando'),
        ('closed', 'Cerrado'),
    ], string="Estado", default="accrual", store=True)
    
    start_date_call = fields.Date(string='Fecha inicio calculo', tracking=True )
    end_date_call = fields.Date(string='Fecha final calculo', tracking=True )
    
    has_advance = fields.Boolean(string="¿Habilitar Adelanto?")
    has_discounts = fields.Boolean(string="¿Habilitar Descuentos?")    
    advance_days = fields.Float(string='Días de Adelanto Vacaciones', default=0)
    days_not_work = fields.Float(string="Días No Trabajados", default=0)

    # Selección de jornada (puedes añadirla si no la tienes)
    working_days_per_week = fields.Selection([
        ('5', '5 días a la semana'),
        ('6', '6 días a la semana')
    ], string="Jornada Laboral", default='5')

    # Campo que muestra el mínimo legal (informativo)
    min_effective_days = fields.Integer(
        string="Mínimo Días Efectivos (D.L. 713)",
        compute="_compute_min_days"
    )
    
    # Fecha máxima para tomar las vacaciones de este periodo
    enjoyment_deadline = fields.Date(
        string="Fecha Límite para Goce",
        compute="_compute_enjoyment_deadline",
        store=True,
        help="Fecha máxima para disfrutar el descanso sin generar indemnización (D.L. 713)"
    )
    
    _sql_constraints = [
        (
            "unique_employee_year",
            "unique(employee_id, year, company_id)",
            "Ya existe un registro de acumulación para este Empleado y este Año Periodo."
        )
    ]

    ######################################################
    #Generacion de contendor de año-periodo de acumulacion
    @api.depends('start_date')
    def _compute_period_data(self):
        for rec in self:
            if rec.start_date:
                # El fin es un año después menos un día
                d_start = fields.Date.from_string(rec.start_date)
                d_end = d_start + relativedelta(years=1) - relativedelta(days=1)
                
                rec.end_date = d_end
                
                # Generamos el formato 2021-22
                # Usamos %y para obtener los últimos dos dígitos (22)
                year_start = d_start.strftime('%Y')
                year_end = d_end.strftime('%y')
                rec.year = f"{year_start}-{year_end}"
            else:
                rec.end_date = False
                rec.year = False
                
    @api.depends('year', 'employee_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.year and rec.employee_id:
                # Ejemplo: "2021-22 / Juan Pérez"
                rec.display_name = f"{rec.year} / {rec.employee_id.name}"
            else:
                rec.display_name = "Nuevo Registro de Vacaciones"
    
    #Metodo para mostrar Dias Efectivos           
    @api.depends('working_days_per_week')
    def _compute_min_days(self):
        for rec in self:
            if rec.working_days_per_week == '5':
                rec.min_effective_days = 210
            else:
                rec.min_effective_days = 260

    ##FEcha maximo para gozar vacaciones            
    @api.depends('end_date')
    def _compute_enjoyment_deadline(self):
        for rec in self:
            if rec.end_date:
                # El plazo es un año después del cierre del periodo
                d_end = fields.Date.from_string(rec.end_date)
                rec.enjoyment_deadline = d_end + relativedelta(years=1)
            else:
                rec.enjoyment_deadline = False
                
    @api.depends('allocation_ids.days_allocated', 'allocation_ids.state', 'consumed_days_manual')
    def _compute_consumed(self):
        for rec in self:
            approved_allocations = rec.allocation_ids.filtered(lambda a: a.state == 'approved')
            sum_allocated = sum(approved_allocations.mapped('days_allocated'))
            # Sumamos lo calculado de Odoo + lo que subiste históricamente
            rec.consumed_days = sum_allocated + rec.consumed_days_manual
            
    ## calculo de saldo
    @api.depends('accumulated_days', 'consumed_days', 'advance_days')
    def _compute_balance(self):
        for rec in self:
            # Usamos una lógica de suma segura
            accumulated = rec.accumulated_days or 0.0
            advance = rec.advance_days or 0.0
            consumed = rec.consumed_days or 0.0
            
            rec.balance_days = (accumulated + advance) - consumed
    
    ###Metodo de Creacion del regsitro        
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Si el usuario no elige fecha, ponemos hoy por defecto
            if not vals.get('start_date'):
                vals['start_date'] = fields.Date.today()
            
            # Sincronizamos el puntero de cálculo inicial con la fecha de inicio
            # Esto asegura que el primer cálculo empiece desde el día 1 del periodo
            if not vals.get('start_date_call'):
                vals['start_date_call'] = vals['start_date']

        return super(ZVacationYear, self).create(vals_list)
    
    
    #### Meotod de CALCULO para el acmulado
    def _compute_accrual(self, with_message=True):
        """
        Calcula el acumulado incrementalmente.
        """
        RATE = 0.0822
        for rec in self:
            if rec.state == "closed":
                raise UserError("El registro está cerrado y no puede actualizarse.")

            # El cálculo empieza donde quedó el anterior (o en la fecha de inicio)
            start = rec.start_date_call or rec.start_date
            
            # El cálculo llega hasta hoy, pero con tope en la fecha fin del aniversario
            today = fields.Date.today()
            end = min(today, rec.end_date)
            
            # Guardamos la fecha final del cálculo para el puntero
            rec.end_date_call = end

            # Si hoy es el mismo día que 'start', .days dará 0. 
            # Esto evita duplicar días si se pulsa el botón varias veces hoy.
            days_total = (end - start).days
            
            if days_total < 0:
                # Si ya se calculó hasta hoy o el periodo terminó, no hacemos nada
                continue

            # Aplicar descuento de días no trabajados cargados en este tramo
            effective_days = days_total - rec.days_not_work

            if effective_days < 0:
                effective_days = 0

            # Cálculo y suma incremental
            added_days = round(effective_days * RATE, 4)
            rec.accumulated_days += added_days

            # El puntero se mueve al final del tramo actual
            rec.start_date_call = end
            not_worked = rec.days_not_work
            rec.days_not_work = 0 #permite no descontar siempre en cada actualziaicon
            # Nota: rec.days_not_work NO se resetea por tu requerimiento. 
            # El usuario debe manejarlo antes del próximo clic.

            # Solo escribir en el Chatter si se solicita (ej. clic manual)
            if with_message:
                rec.message_post(
                    body=(
                        f"**Actualización Manual:**...."
                        f"Tramo: {start} al {end}...."
                        f"Días naturales: {days_total}...."
                        f"Días no trabajados: {not_worked}...."
                        f"Días añadidos: {added_days}"
                    )
                )
    
    
    # Boton Actualizar
    def action_update_accrual(self):
        # Al pasar True, se genera el mensaje en el Chatter
        return self._compute_accrual(with_message=True)

    
    # Boton Cerrar
    def action_close_accrual(self):
        for rec in self:
            # Aseguramos el último cálculo antes de morir
            rec._compute_accrual()
            rec.state = "closed"
            # No sobreescribimos end_date si ya tenía una, para no romper el historial
            if not rec.end_date:
                rec.end_date = fields.Date.today()
            rec.message_post(body="Ciclo finalizado. Registro cerrado para histórico.")
        return True


    ### CRON
    @api.model
    def _cron_vacation_auto_cycle(self):
        # Gestionar cierres y relevos (estos sí pueden dejar un mensaje de "Cierre")
        today = fields.Date.today()
        expired_records = self.search([('state', '=', 'accrual'), ('end_date', '<=', today)])
        
        for old_rec in expired_records:
            old_rec.action_close_accrual() # El cierre sí es importante que se vea
            
            # Crear relevo
            new_start = old_rec.end_date + relativedelta(days=1)
            self.create({
                'employee_id': old_rec.employee_id.id,
                'start_date': new_start,
                'state': 'accrual',
            })

        # ACTUALIZACIÓN SILENCIOSA DIARIA
        active_records = self.search([('state', '=', 'accrual')])
        # Usamos with_context para indicarle al método que no escriba en el chatter
        active_records.with_context(skip_chatter_log=True).action_update_accrual()
