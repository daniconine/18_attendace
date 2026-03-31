from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    is_overtime = fields.Boolean(
        string="Es Hora Extra",
        default=False,
        help="Indica si este tipo de entrada corresponde a horas extras."
    )
    pe_overtime_code = fields.Selection([
        ('25', 'Hora Extra 25%'),
        ('35', 'Hora Extra 35%'),
        ('night_25', 'Hora Extra Nocturna 25%'),
        ('night_35', 'Hora Extra Nocturna 35%'),
        ('holiday', 'Hora Extra en Feriado 100%'),
        ('sunday', 'Hora Extra en Domingo 100%'),
        ('compensatory', 'Trabajo Compensatorio'),
    ], string="Código de Hora Extra (PE)",
       help="Identifica este tipo de entrada para ser usado en las solicitudes de horas extras automáticas.")
    
    is_compensatory_leave = fields.Boolean(
        string="Es Permiso Compensatorio",
        help="Marcar si este tipo de entrada representa un permiso que consume horas del saldo compensatorio."
    )
    is_vacation_leave = fields.Boolean(
        string="Consume Saldo de Vacaciones",
        help="Marcar si este tipo de entrada representa una ausencia que consume días del saldo de vacaciones del contrato."
    )
    is_advanced_vacation_type = fields.Boolean(
        string="Es un Adelanto de Vacaciones",
        help="Marcar si este tipo de ausencia debe ser tratado como un adelanto, "
             "ignorando el saldo actual pero validando la política del contrato."
    )
    is_working_day = fields.Boolean(
        string="Es un Día de Trabajo",
        help="Marcar si este tipo de entrada debe ser tratado como un día laborado."
    )

    @api.constrains('is_compensatory_leave', 'is_vacation_leave')
    def _check_exclusive_leave_type(self):
        for record in self:
            if record.is_compensatory_leave and record.is_vacation_leave:
                raise ValidationError(
                    _("Un tipo de entrada de trabajo no puede ser para 'Permiso Compensatorio' y 'Vacaciones' al mismo tiempo.")
                )