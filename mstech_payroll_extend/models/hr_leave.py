from odoo import models, fields, api
from odoo.exceptions import UserError

class HrLeave(models.Model):
    _inherit = 'hr.leave'


    payslip_status = fields.Selection([
        ('calculate_in_next', 'A calcular en el siguiente recibo de nómina'),
        ('calculated', 'Ya calculado en un recibo'),
        ('excluded', 'No incluir en recibo'),
    ], string='Estado del recibo de nómina', default='calculate_in_next')

    """
    plame_suspension_type_id = fields.Many2one(
        'hr.plame.suspension.type',
        string="Tipo de Suspensión (PLAME)",
        help="Código oficial de SUNAT para este tipo de ausencia, usado en la declaración del PLAME."
    )
    """

    def _check_balances(self):
        """     Método unificado que llama a todas las validaciones de saldo.  """
        self._check_compensatory_balance()
        self._check_vacation_balance()


    def _check_compensatory_balance(self):
        """     Verifica si el tipo de ausencia es compensatorio y si hay saldo suficiente.      """
        for leave in self:
            work_entry_type = leave.holiday_status_id.work_entry_type_id
            if not work_entry_type.is_compensatory_leave:
                continue

            contract = leave.employee_id.contract_id
            
            if not contract or contract.state != 'open':
                raise UserError(f"El empleado {leave.employee_id.name} no tiene un contrato activo para validar el saldo de horas.")

            duration_hours = leave.number_of_hours_display
            if contract.compensatory_hours_balance < duration_hours:
                raise UserError(
                    f"Saldo insuficiente. El empleado {leave.employee_id.name} tiene "
                    f"{contract.compensatory_hours_balance:.2f} horas de saldo, "
                    f"pero la solicitud es por {duration_hours:.2f} horas."
                )
            
    def _check_vacation_balance(self):
        """      Verifica si hay saldo de vacaciones suficiente, a menos que sea un adelanto.    """
        for leave in self:
            work_entry_type = leave.holiday_status_id.work_entry_type_id
            
            # Si no es un tipo de ausencia que consume vacaciones, no hacemos nada.
            if not work_entry_type.is_vacation_leave:
                continue

            contract = leave.employee_id.contract_id
            if not contract or contract.state != 'open':
                raise UserError(f"El empleado {leave.employee_id.name} no tiene un contrato activo.")
            
            # --- Lógica de Adelanto de Vacaciones ---
            if work_entry_type.is_advanced_vacation_type:
                if not contract.allow_vacation_advance:
                    raise UserError(
                        f"El contrato de {leave.employee_id.name} no permite el 'Adelanto de Vacaciones'. "
                        "Por favor, revise la configuración del contrato."
                    )
                # Si se permite el adelanto, la validación termina aquí. Dejamos que el saldo se vuelva negativo.
                continue

            # Usamos el campo number_of_days para ausencias en días
            duration_days = leave.number_of_days
            if contract.vacation_days_balance < duration_days:
                raise UserError(
                    f"Saldo de vacaciones insuficiente. El empleado {leave.employee_id.name} tiene "
                    f"{contract.vacation_days_balance} días de saldo, pero la solicitud es por {duration_days} días."
                )

    # --- ACCIONES ---
    def action_approve(self):
        # Primero, hacemos TODAS las validaciones de saldo ANTES de la aprobación.
        self._check_balances()

        # Llamamos al método original
        res = super().action_approve()

        # Ahora, descontamos los saldos correspondientes
        for leave in self:
            contract = leave.employee_id.contract_id
            if not contract:
                continue

            # Lógica para Horas Compensatorias
            if leave.holiday_status_id.work_entry_type_id.is_compensatory_leave:
                duration_hours = leave.number_of_hours_display
                new_balance = contract.compensatory_hours_balance - duration_hours
                contract.write({'compensatory_hours_balance': new_balance})
                contract.message_post(
                    body=f"Se descontaron <b>{duration_hours:.2f} horas</b> del saldo compensatorio por la ausencia <b>{leave.display_name}</b>. Nuevo saldo: {new_balance:.2f} horas."
                )
            
            # Lógica para Días de Vacaciones
            elif leave.holiday_status_id.work_entry_type_id.is_vacation_leave:
                duration_days = leave.number_of_days
                new_balance = contract.vacation_days_balance - duration_days
                contract.write({'vacation_days_balance': new_balance})
                contract.message_post(
                    body=f"Se descontaron <b>{duration_days} días</b> del saldo de vacaciones por la ausencia <b>{leave.display_name}</b>. Nuevo saldo: {new_balance} días."
                )
        return res

    # --- REVERSIONES ---
    def _reverse_deductions(self):
        """    Método unificado que llama a todas las reversiones de saldos.    """
        self._reverse_compensatory_deduction()
        self._reverse_vacation_deduction()

    def _reverse_compensatory_deduction(self):
        """      Devuelve las horas al saldo si una ausencia compensatoria se cancela o rechaza.     """
        for leave in self.filtered(lambda l: l.state == 'validate' and l.holiday_status_id.work_entry_type_id.is_compensatory_leave):
            contract = leave.employee_id.contract_id
            if not contract:
                continue

            duration_hours = leave.number_of_hours_display
            new_balance = contract.compensatory_hours_balance + duration_hours
            contract.write({'compensatory_hours_balance': new_balance})

            contract.message_post(
                body=f"Se acreditaron <b>{duration_hours:.2f} horas</b> al saldo compensatorio "
                     f"debido a la cancelación/rechazo de la ausencia <b>{leave.display_name}</b>. Nuevo saldo: {new_balance:.2f} horas."
            )

    def _reverse_vacation_deduction(self):
        """      Devuelve los días al saldo si una ausencia de vacaciones se cancela o rechaza.     """
        for leave in self.filtered(lambda l: l.state == 'validate' and l.holiday_status_id.work_entry_type_id.is_vacation_leave):
            contract = leave.employee_id.contract_id
            if not contract:
                continue

            duration_days = leave.number_of_days
            new_balance = contract.vacation_days_balance + duration_days
            contract.write({'vacation_days_balance': new_balance})

            contract.message_post(
                body=f"Se acreditaron <b>{duration_days} días</b> al saldo de vacaciones por la cancelación/rechazo de la ausencia <b>{leave.display_name}</b>. Nuevo saldo: {new_balance} días."
            )

    def action_refuse(self):
        self._reverse_deductions()
        return super().action_refuse()

    def action_draft(self):
        self._reverse_deductions()
        return super().action_draft()