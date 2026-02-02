# Tabla Intermedia

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ZVacationAllocateYear(models.Model):
    _name = 'zleave.zvacation.allocate.year'
    _description = 'Asignación de días por periodo de vacaciones'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    company_id = fields.Many2one("res.company", string="Compañía",
                                 default=lambda self: self.env.company, required=True, readonly=True)
    
    vacation_id = fields.Many2one(
        'zleave.zvacation',
        string='Solicitud'
    )

    vacation_year_id = fields.Many2one(
        'zleave.zvacation.year',
        string='Año Acumulado de Vacaciones',
        required=True
    )

    days_allocated = fields.Float(
        string='Días asignados',
        required=True
    )

    # Estado sincronizado con la solicitud
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Enviado'),
        ('approved', 'Aprobado'),
        ('refused', 'Rechazado'),
        ('cancelled', 'Anulado'),
    ], string="Estado", compute="_compute_state", store=True)

    ########################################
    ###mapeo del estado en zvacation
    @api.depends('vacation_id.state')
    def _compute_state(self):
        for rec in self:
            rec.state = rec.vacation_id.state


    ##########################################################
    #   MÉTODO FIFO PARA GENERAR ASIGNACIONES AUTOMÁTICAMENTE
    @api.model
    def allocate_days_for_vacation(self, vacation):
        """Aplica FIFO y crea las líneas preliminares de asignación."""

        remaining_days = vacation.duration_days
        employee = vacation.employee_id

        if remaining_days <= 0:
            return

        # Buscar años con saldo > 0 (FIFO)
        vacation_years = self.env['zleave.zvacation.year'].search([
            ('company_id', '=', vacation.company_id.id),
            ('employee_id', '=', employee.id),
            ('balance_days', '>', 0),
        ], order="year asc")

        allocation_summary = []
        total_allocated = 0  # ← para calcular los días que SÍ se pueden usar

        for year in vacation_years:
            if remaining_days <= 0:
                break

            available = year.balance_days
            days_to_allocate = min(available, remaining_days)

            # Crear asignación preliminar FIFO
            self.create({
                'vacation_id': vacation.id,
                'vacation_year_id': year.id,
                'days_allocated': days_to_allocate,
            })

            allocation_summary.append(
                f"- {days_to_allocate} día(s) del año {year.year}"
            )

            total_allocated += days_to_allocate
            remaining_days -= days_to_allocate

        # --- REDONDEOS ---
        usable_days = int(total_allocated)               # Días enteros utilizables
        missing_days = int(vacation.duration_days - usable_days)

        # Si faltan días → error con mensaje claro
        if usable_days < vacation.duration_days:
            raise ValidationError(_(
                f"El empleado {employee.name} no tiene saldo suficiente para esta solicitud.\n\n"
                f"• Días solicitados: {vacation.duration_days}\n"
                f"• Días disponibles según FIFO: {total_allocated}\n"
                f"• Días utilizables (enteros): {usable_days}\n"
                f"• Días faltantes: {missing_days}\n\n"
                f"Modifique la solicitud para que solo incluya los {usable_days} día(s) disponibles.\n"
                f"Los {missing_days} día(s) restantes deben solicitarse como "
                f"Vacaciones Adelantadas en una nueva solicitud."
            ))

        # Mensaje en el chatter
        if allocation_summary:
            msg = "Asignación automática preliminar (FIFO):<br/>" + "<br/>".join(allocation_summary)
            vacation.message_post(body=msg)