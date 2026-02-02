######################
####### MODLEO DE ACUMUALCION DE VACACIONES

from odoo import models, fields, api
from datetime import datetime
from datetime import date

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
    year = fields.Char(string='Año', required=True)
    start_date = fields.Date(string='Fecha inicial Acumulación', default=fields.Date.today)
    end_date = fields.Date(string='Fecha final Acumulación' )
    accumulated_days = fields.Float(string='Días Acumulados')
    consumed_days = fields.Float(string='Días Consumidos')
    balance_days = fields.Float(string='Saldo', compute='_compute_balance', store=True)
    
    # Relación con la tabla puente
    allocation_ids = fields.One2many('zleave.zvacation.allocate.year',
        'vacation_year_id', string='Vacaciones Asignadas' )
    vacation_id = fields.Many2one('zleave.zvacation', string='Solicitud de Vacaciones', ondelete='cascade')

    

    display_name = fields.Char( string="Nombre", compute="_compute_display_name",
                            store=True )
          
    state = fields.Selection([
        ('accrual', 'Acumulando'),
        ('closed', 'Cerrado'),
    ], string="Estado", default="accrual", store=True)
    
    start_date_call = fields.Date(string='Fecha inicio calculo', tracking=True )
    end_date_call = fields.Date(string='Fecha final calculo', tracking=True )
    advance_days = fields.Float(string='Días de Adelanto Vacaciones', default=0)
    
    days_not_work = fields.Float(string="Días No Trabajados", default=0)

    _sql_constraints = [
        (
            "unique_employee_year",
            "unique(employee_id, year, company_id)",
            "Ya existe un registro de acumulación para este empleado y este año."
        )
    ]

    #############################################
    # RESTRICCIÓN PYTHON (antes de crear)
    @api.model_create_multi
    def create(self, vals_list):

        # --- Validaciones previas ---
        for vals in vals_list:

            employee = vals.get("employee_id")
            year = vals.get("year")

            if employee and year:
                # Buscar si ya existe un registro NO CERRADO del mismo empleado y año
                exists = self.env["zleave.zvacation.year"].search([
                    ("employee_id", "=", employee),
                    ("year", "=", year),
                    ("state", "!=", "closed"),
                ], limit=1)

                if exists:
                    raise UserError(
                        f"Ya existe un registro activo de acumulación para el empleado "
                        f"{exists.employee_id.name} en el año {year}. "
                        "Debe cerrarse antes de crear uno nuevo."
                    )

            # --- Asignar start_date_call si no se envió ---
            if vals.get("start_date"):
                vals.setdefault("start_date_call", vals["start_date"])
            else:
                today = fields.Date.today()
                vals.setdefault("start_date", today)
                vals.setdefault("start_date_call", today)

            # --- Crear end_date automáticamente al 31 de diciembre del año ---
            if "end_date" not in vals or not vals.get("end_date"):
                if year:
                    vals["end_date"] = date(int(year), 12, 31)

        # === Crear los registros como RECORDSET real ===
        records = super(ZVacationYear, self).create(vals_list)

        return records

    ########## Creacion de nombre    
    @api.depends('year', 'employee_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.year} – {rec.employee_id.name}"

    ##calculo de saldo
    @api.depends('accumulated_days', 'consumed_days', 'advance_days')
    def _compute_balance(self):
        for rec in self:
            rec.balance_days = rec.advance_days + rec.accumulated_days - rec.consumed_days
    
    
    #######################################
    #CAlculo        
    def _compute_accrual(self):
        """
        Calcula el acumulado restando días no trabajados.
        Fórmula:
            (end_date_call - start_date_call + 1 - days_not_work) * 0.0822
        Luego:
            start_date_call = end_date_call
            days_not_work = 0
        """

        RATE = 0.0822  # días acumulados por día trabajado

        for rec in self:

            if rec.state == "closed":
                raise UserError("El registro está cerrado y no puede actualizarse.")

            start = rec.start_date_call or rec.start_date
            end = fields.Date.today()
            rec.end_date_call = end

            if end < start:
                raise UserError("La fecha final no puede ser menor que la fecha inicial.")

            # Días transcurridos
            days_total = (end - start).days
            
            # Aplicar descuento manual de días no trabajados
            effective_days = days_total - rec.days_not_work

            if effective_days < 0:
                effective_days = 0   # seguridad total

            # Cálculo final
            added_days = round(effective_days * RATE, 4)

            # Sumar al acumulado
            rec.accumulated_days += added_days

            # Reset de control
            rec.start_date_call = end
            rec.days_not_work = 0

            # Trazabilidad
            rec.message_post(
                body=(
                    f"Actualización de acumulación:<br/>"
                    f"• Días naturales: {days_total}<br/>"
                    f"• Días no trabajados: {rec.days_not_work}<br/>"
                    f"• Días efectivos: {effective_days}<br/>"
                    f"• Días añadidos: {added_days}"
                )
            )
            
            
    #Boton Actualizar
    def action_update_accrual(self):
        for rec in self:
            rec._compute_accrual()
        return True

    
    #Boton Cerrar
    def action_close_accrual(self):
        for rec in self:
            rec._compute_accrual()
            rec.state = "closed"
            rec.end_date = fields.Date.today()
            rec.message_post(body="Acumulación cerrada y saldo actualizado. Si es fin de año crear otro")
        return True

   