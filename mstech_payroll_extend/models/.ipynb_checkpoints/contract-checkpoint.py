# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # ===============================================
    # ➤ Régimen laboral y pensiones (Perú)
    # ===============================================

    pe_labor_regime_id = fields.Many2one(
        'hr.labor.regime.pe',
        string="Régimen Laboral",
        tracking=True
    )

    pe_pension_scheme = fields.Selection([
        ('onp', 'ONP'),
        ('spp', 'SPP'),
    ], string="Régimen Pensionario", tracking=True)

    afp_id = fields.Many2one(
        'hr.afp', string='AFP (si aplica)', tracking=True
    )

    afp_commission_type = fields.Selection([
        ('flow', 'Sobre el flujo'),
        ('mixed', 'Mixta'),
        ('mixed2', 'Mixta 2.0'),
    ], string='Tipo de comisión AFP', tracking=True)

    pe_health_scheme = fields.Selection([
        ('essalud_regular', 'ESSALUD REGULAR'),
        ('eps', 'EPS'),
        ('essalud_sctr', 'SCTR ESSALUD'),
        ('eps_sctr', 'SCTR EPS'),
        ('sis', 'SIS'),
    ], string='Régimen de salud', tracking=True)

    # ===============================================
    # ➤ Conceptos remunerativos adicionales
    # ===============================================

    food_allowance = fields.Monetary(
        string='Alimentación principal en dinero'
    )

    productivity_bonus = fields.Monetary(
        string='Bono de Productividad'
    )

    eps_cost = fields.Monetary(
        string='Costo EPS'
    )

    mobility_allowance = fields.Monetary(
        string='Movilidad de libre disposición'
    )

    sctr_table = fields.Selection([
        ('sctr_public', 'SCTR Público'),
        ('sctr_private_percentage', 'SCTR Privado Porcentaje'),
        ('sctr_private_flat', 'SCTR Privado Monto fijo'),
    ], string='Tabla SCTR')

    # ===============================================
    # ➤ Descuentos judiciales
    # ===============================================

    judicial_deduction_type = fields.Selection([
        ('fixed', 'Fijo'),
        ('percent', 'Porcentaje'),
    ], string='Tipo de retención judicial')

    judicial_deduction_amount = fields.Monetary(
        string='Descuento judicial'
    )

    # ===============================================
    # ➤ Cálculo de la renta de 5ta categoría
    # ===============================================

    receives_commissions = fields.Boolean(string='Percibe comisiones')

    estimated_monthly_bonuses = fields.Monetary(
        string='Bonificaciones regulares mensuales estimadas'
    )

    estimated_commissions = fields.Monetary(
        string='Comisiones o destajo mensuales estimadas'
    )

    previous_income_total = fields.Monetary(
        string='Total de remuneraciones anteriores del periodo',
        help="Solo será utilizado en nóminas del mismo año de inicio del contrato."
    )
    
    previous_rent5_held = fields.Monetary(
        string='Total de retenciones anteriores del periodo',
        help="Solo será utilizado en nóminas del mismo año de inicio del contrato."
    )

    # ===============================================
    # ➤ para logica de tardanzas
    # ===============================================
    overtime_tolerance_minutes = fields.Float(
        string="Tolerancia de Tardanza (minutos)",
        default=5,
        help="Minutos de tolerancia antes de considerar tardanza."
    )

    overtime_generation_tolerance = fields.Float(
        string="Tolerancia para Generar H.E. (minutos)",
        default=15,
        help="El empleado debe trabajar al menos esta cantidad de minutos extra para que se genere una solicitud de horas extras."
    )

    tardiness_type_1h = fields.Many2one(
        'hr.leave.type',
        string="Ausencia por tardanza ≤ 1 hora",
        help="Tipo de ausencia que se genera cuando la tardanza es menor o igual a 1 hora."
    )

    tardiness_type_2h = fields.Many2one(
        'hr.leave.type',
        string="Ausencia por tardanza ≤ 2 horas",
        help="Tipo de ausencia que se genera cuando la tardanza es mayor a 1 hora pero menor o igual a 2 horas."
    )

    tardiness_type_more = fields.Many2one(
        'hr.leave.type',
        string="Ausencia por tardanza > 2 horas",
        help="Tipo de ausencia que se genera cuando la tardanza supera las 2 horas."
    )

    # ===============================================
    # ➤ para logica de tiempos compensatorios
    # ===============================================

    compensatory_hours_balance = fields.Float(
        string="Saldo de Horas Compensatorias",
        tracking=True,
        help="Saldo acumulado de horas de permiso compensatorio. Puede ser positivo o negativo."
    )

    vacation_days_balance = fields.Integer(
        string="Saldo de Vacaciones (días)",
        tracking=True,
        help="Saldo acumulado de días de vacaciones. Se ajusta anualmente y por ausencias.",
        readonly=True, # Recomendado que sea solo lectura
        default=0
    )
    
    last_vacation_accrual_date = fields.Date(
        string="Última Fecha de Devengo de Vacaciones",
        readonly=True,
        copy=False,
        help="La fecha en la que se calculó el último devengo anual de vacaciones para este contrato."
    )

    is_trusted_employee = fields.Boolean(
        string="Personal de Confianza o Dirección",
        tracking=True,
        help="Marcar esta casilla si el trabajador es calificado como personal de confianza o de dirección."
    )

    special_situation = fields.Selection(string="Situación especial", selection=[
        ("0", "NINGUNA"),
        ("1", "TRABAJADOR DE DIRECCIÓN – PRESENCIAL"),
        ("2", "TRABAJADOR DE CONFIANZA - PRESENCIAL"),
        ("3", "TRABAJADOR DE DIRECCIÓN - TELETRABAJO MIXTO"),
        ("4", "TRABAJADOR DE CONFIANZA - TELETRABAJO MIXTO"),
        ("5", "TRABAJADOR DE DIRECCIÓN - TELETRABAJO COMPLETO"),
        ("6", "TRABAJADOR DE CONFIANZA - TELETRABAJO COMPLETO"),
        ("7", "TELETRABAJO MIXTO"),
        ("8", "TELETRABAJO COMPLETO")
    ], default="0")


    allow_vacation_advance = fields.Boolean(
        string="Permitir Adelanto de Vacaciones",
        tracking=True,
        help="Si se marca, el empleado podrá tomar vacaciones incluso si su saldo es cero o negativo, "
             "siempre que el tipo de ausencia sea 'Adelanto de Vacaciones'."
    )

    bank_id = fields.Many2one('res.bank', string="Banco de Pago")
    bank_account_number = fields.Char(string="Número de Cuenta de Pago")
    bank_account_currency = fields.Many2one(string="Moneda de Cuenta de Pago", comodel_name="res.currency", default=lambda self: self.env.company.currency_id)

    formative_modality_id = fields.Many2one(string="Modalidad formativa", comodel_name="hr.formative.modality")
    job_occupation_id = fields.Many2one(string="Ocupación", comodel_name="hr.job.occupation")
    has_atypical_hours = fields.Boolean(string="Sujeto a régimen alternativo, acumulativo o atípico de jornada de trabajo y descanso")
    has_maximum_hours = fields.Boolean(string="Sujeto a jornada de trabajo máxima")
    has_night_hours = fields.Boolean(string="Sujeto a horario nocturno")
    is_unionized = fields.Boolean(string="Es sindicalizado")

    def _get_contract_work_entries_values(self, date_start, date_stop):
        """
        exclude holidays (leave_id=False)
        """
        res = super()._get_contract_work_entries_values(date_start, date_stop)
        """ TODO: only exclude if need?
        if 'ignore_holidays' in self.env.context:
            res = [val for val in res if 'leave_id' in val]
        """
        res = [val for val in res if val.get('leave_id') != False]
        return res
            
    @api.model
    def _cron_accrue_annual_vacation(self):
        """
        Este método, llamado por un cron, busca empleados que han cumplido un año de servicio
        y les asigna los días de vacaciones correspondientes a su régimen laboral.
        """
        today = fields.Date.today()
        # Buscamos solo contratos activos que tengan un régimen definido
        active_contracts = self.search([
            ('state', '=', 'open'),
            ('pe_labor_regime_id', '!=', False)
        ])

        for contract in active_contracts:
            # Usamos la fecha del primer contrato del empleado para calcular la antigüedad total
            start_date = contract.employee_id.first_contract_date
            if not start_date:
                continue

            # Determinamos la última fecha de devengo para saber desde dónde calcular
            last_accrual = contract.last_vacation_accrual_date or start_date
            
            # Usamos un bucle para el caso de que el cron no se haya ejecutado por varios años
            while True:
                next_anniversary = last_accrual + relativedelta(years=1)
                
                # Si el próximo aniversario aún no ha llegado, salimos del bucle para este contrato
                if next_anniversary > today:
                    break

                # ¡El empleado ha cumplido otro año! Procedemos a devengar.
                days_to_add = contract.pe_labor_regime_id.annual_vacation_days
                if days_to_add > 0:
                    new_balance = contract.vacation_days_balance + days_to_add
                    contract.write({
                        'vacation_days_balance': new_balance,
                        'last_vacation_accrual_date': next_anniversary
                    })
                    
                    # Dejamos un registro en el chatter del contrato para auditoría
                    contract.message_post(
                        body=f"Se acreditaron <b>{days_to_add} días</b> de vacaciones por el aniversario del "
                             f"{next_anniversary.strftime('%d/%m/%Y')}. Nuevo saldo: {new_balance} días."
                    )
                
                # Actualizamos la fecha del último devengo para la siguiente iteración del bucle
                last_accrual = next_anniversary

class HrLaborRegimePE(models.Model):
    _name = 'hr.labor.regime.pe'
    _description = 'Régimen Laboral (Perú)'
    _order = 'name'

    name = fields.Char(string='Nombre del Régimen', required=True)
    code = fields.Char(string='Código', help="Código interno o del decreto ley, ej: 728, MYPE")
    plame_code = fields.Char(string='Código en PLAME')
    annual_vacation_days = fields.Integer(
        string='Días de Vacaciones Anuales',
        required=True,
        default=0,
        help="Número de días de vacaciones que un empleado gana al cumplir un año de servicio bajo este régimen."
    )
    active = fields.Boolean(default=True)
    receives_gratification = fields.Boolean(string="Recibe gratificaciones", default=True)
