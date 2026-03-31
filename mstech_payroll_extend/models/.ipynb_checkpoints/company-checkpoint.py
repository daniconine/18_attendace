from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ➤ Representante legal
    legal_representative_id = fields.Many2one(
        comodel_name='res.partner',
        string='Representante legal',
        help='Persona registrada como representante legal ante SUNAT.'
    )
    legal_rep_dni = fields.Char(
        related='legal_representative_id.vat',
        string='DNI del representante legal',
        readonly=True,
        store=True
    )
    legal_rep_position = fields.Char(
        related='legal_representative_id.function',
        string='Cargo del representante legal',
        readonly=True,
        store=True
    )
    legal_rep_signature = fields.Binary(string="Firma del representante legal")
    
    # ➤ Políticas internas
    enforce_commission_in_soles = fields.Boolean(string="Comisiones: Descuentos solo en soles")
    discount_holidays_on_vac = fields.Boolean(string="Descontar feriados en vacaciones gozadas")
    discount_day_31_on_vac = fields.Boolean(string="Descontar día 31 en vacaciones")
    min_vacation_days = fields.Integer(string="Duración mínima de salida de vacaciones (días)")
    discount_unpaid_days_in_quincena = fields.Boolean(string="Quincena: Descontar días no pagados")

    # ➤ Actividad económica (utilidades)
    activity_utilities_id = fields.Many2one(
        comodel_name='pe.economic.activity',
        string='Actividad económica para distribución de utilidades'
    )

    enable_payroll_analytic_distribution = fields.Boolean(
        string="Activar Distribución Analítica de Nómina",
        help="Si se marca, al confirmar una nómina, el sistema distribuirá el costo "
             "entre los centros de costo basándose en los partes de horas."
    )
