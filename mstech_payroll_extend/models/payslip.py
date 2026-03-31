# mstech_payroll_extend/models/payslip.py

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from datetime import date, datetime, time, timedelta
from collections import defaultdict
from pytz import timezone

import logging

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    is_liquidation = fields.Boolean(
        string="Es una Liquidación",
        help="Marcar esta casilla si esta nómina corresponde a una liquidación de beneficios sociales."
    )

    analytic_cost_line_ids = fields.One2many(
        'hr.payslip.analytic.cost',
        'payslip_id',
        string="Distribución de Costo Analítico"
    )

    
    # =========================================================================
    # ➤ MÉTODO PRINCIPAL DE CÁLCULO (COMPUTE_SHEET)
    # =========================================================================
    def compute_sheet(self):
        # ➤ CORRECCIÓN CLAVE: Regeneramos las entradas de trabajo ANTES de cualquier cálculo.
        for payslip in self:
            _logger.info(f"Regenerando entradas de trabajo para la nómina {payslip.number}...")
            #payslip.action_generate_work_entries()
            regen_wizard = self.env['hr.work.entry.regeneration.wizard'].create({
                'employee_ids': [fields.Command.set(payslip.employee_id.ids)],
                'date_from': payslip.date_from,
                'date_to': payslip.date_to,
            })
            regen_wizard.regenerate_work_entries()
        
        # Ahora que las entradas están frescas, llamamos al método original de compute_sheet,
        # que a su vez llamará a nuestros métodos heredados (_get_worked_day_lines, etc.)
        res = super().compute_sheet()

        # Asigna el código plame que corresponde a cada línea
        for payslip in self:
            for line in payslip.line_ids:
                line.plame_code = line.salary_rule_id.plame_code
        
        return res
    
    
    # =========================================================================
    # ➤ 1. GENERACIÓN DE LÍNEAS DE DÍAS TRABAJADOS (WORKED DAYS)
    # =========================================================================
    # Heredamos el método que Odoo usa para calcular los días trabajados.
    # Al sobreescribirlo, tomamos control total.
    #def _get_worked_day_lines(self):
    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):

        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            calendar = contract.resource_calendar_id
            employee_id = contract.employee_id
            tz = timezone(calendar.tz)
            
            # Buscamos todas las entradas de trabajo validadas para este contrato y período
            work_entries = self.env['hr.work.entry'].search([
                ('employee_id', '=', employee_id.id),
                ('date_start', '<=', date_to),
                ('date_stop', '>=', date_from),
                #('state', 'in', ['validated']),
                ('state', 'in', ['draft']),
                ('contract_id', '=', contract.id),
            ])
    
            # Usamos defaultdict para agrupar las horas por tipo de entrada
            grouped_hours = defaultdict(float)
            for entry in work_entries:
                grouped_hours[entry.work_entry_type_id] += entry.duration
    
            for work_entry_type, total_hours in grouped_hours.items():
                days = total_hours / (calendar.hours_per_day or 8.0)
                
                line_vals = {
                    'name': work_entry_type.name,
                    'code': work_entry_type.code,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_hours': total_hours,
                    'number_of_days': days,
                    'contract_id': contract.id,
                    #'payslip_id': self.id,
                }
                res.append(line_vals)
            
            # Devolvemos una lista vacía porque ya hemos creado las líneas directamente.
        return res

    # =========================================================================
    # ➤ 2 & 3. GENERACIÓN DE OTRAS ENTRADAS (BONOS Y COMISIONES)
    # =========================================================================
    # Heredamos el onchange para que se ejecute al preparar la boleta.
    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        res = super().onchange_employee()
        
        if not self.employee_id or not self.date_from or not self.date_to:
            return res

        new_input_lines_vals = []
        
        # --- Lógica para Bonos (Detallado) ---
        bonuses = self.env['hr.bonus'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '<=', self.date_to),
            ('state', '=', 'draft'),
        ])
        for bonus in bonuses:
            new_input_lines_vals.append((0, 0, {
                'name': bonus.payslip_description,
                'code': bonus.payslip_code,
                'amount': bonus.amount,
                'contract_id': self.contract_id.id,
            }))

        # --- Lógica para Comisiones (Aglomerado) ---
        commissions = self.env['hr.commission'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '<=', self.date_to),
            ('state', '=', 'draft'),
        ])
        
        if commissions:
            total_commission_amount = sum(comm.amount for comm in commissions)
            # Necesitamos un 'tipo de entrada' genérico para las comisiones.
            # Lo ideal es crearlo en un archivo de datos y referenciarlo aquí.
            commission_input_config = commissions[0].config_id # Tomamos la config de la primera comisión
            
            new_input_lines_vals.append((0, 0, {
                'name': commission_input_config.payslip_description, # ej: "Comisiones por Ventas"
                'code': commission_input_config.payslip_code,       # ej: "COMISIONES"
                'amount': total_commission_amount,
                'contract_id': self.contract_id.id,
            }))

        # Borramos las entradas anteriores y añadimos las nuevas.
        self.input_line_ids = [(5, 0, 0)]
        if new_input_lines_vals:
            self.input_line_ids = new_input_lines_vals
        
        return res

    # =========================================================================
    # ➤ ACCIÓN DE CONFIRMACIÓN (PARA ACTUALIZAR ESTADOS)
    # =========================================================================
    def action_payslip_done(self):
        res = super().action_payslip_done()
        for payslip in self:
            # Marcar Bonos como 'done'
            bonuses_to_mark = self.env['hr.bonus'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('date', '<=', payslip.date_to),
                ('state', '=', 'draft'),
            ])
            if bonuses_to_mark:
                bonuses_to_mark.write({'state': 'done', 'payslip_id': payslip.id})

            # Marcar Comisiones como 'done'
            commissions_to_mark = self.env['hr.commission'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('date', '<=', payslip.date_to),
                ('state', '=', 'draft'),
            ])
            if commissions_to_mark:
                commissions_to_mark.write({'state': 'done', 'payslip_id': payslip.id})

            payslip._generate_analytic_cost_distribution()
                
        return res
    
    def rule_parameter(self, code, date=None):
        """
        Busca el valor de un parámetro salarial para una fecha determinada.
        Si no se provee una fecha, usa la fecha de fin de la nómina.
        """
        self.ensure_one()
        if not date:
            date = self.date_to
        
        # Buscamos la versión del parámetro cuya fecha de inicio sea la más cercana
        # pero no posterior a la fecha de la nómina.
        version = self.env['hr.rule.parameter.version'].search([
            ('parameter_id.code', '=', code),
            ('date_from', '<=', date)
        ], limit=1, order='date_from DESC')
        
        if not version:
            # Es buena idea lanzar un error si el parámetro no se encuentra,
            # para evitar cálculos silenciosamente incorrectos.
            raise ValidationError(
                _("No se encontró un valor para el parámetro salarial con código '%s' para la fecha %s.") %
                (code, date)
            )
        
        return version.value
    
    def _generate_analytic_cost_distribution(self):
        """
        Calcula y distribuye el costo de la nómina de forma precisa:
        1. Asigna los sobre-costos (extras, nocturnos) directamente al centro de costo donde ocurrieron.
        2. Prorratea los costos base (sueldo, aportes) según las horas regulares.
        """
        self.ensure_one()
        self.analytic_cost_line_ids.unlink()

        if not self.company_id.enable_payroll_analytic_distribution:
            return # Si no está activado, no hacemos nada.
        # --- PREPARACIÓN DE DATOS ---
        contract = self.contract_id
        if not contract: return

        # 1. Obtener todas las Hojas de Horas (Timesheets) del período
        timesheets = self.env['account.analytic.line'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from), ('date', '<=', self.date_to),
        ])
        _logger.info('\n\n'+str(timesheets)+'\n')
        if not timesheets: return # Si no hay parte de horas, no se puede distribuir.

        # 2. Calcular el valor de una hora de trabajo normal
        calendar = contract.resource_calendar_id
        monthly_hours = (calendar.hours_per_day or 8.0) * 30 # Aproximación
        hourly_wage = contract.wage / monthly_hours if monthly_hours else 0

        # 3. Identificar las reglas que generan un costo para la empresa
        all_cost_lines = self.line_ids.filtered(lambda l: l.category_id.code in ['BASIC_PE', 'ALW_PE', 'EMP_CONT_PE', 'PROV_PE'])
        
        # Diccionario para acumular los costos por cuenta analítica
        costs_by_analytic = defaultdict(lambda: defaultdict(float))

        # --- PASO 1: ASIGNACIÓN DIRECTA DE SOBRE-COSTOS ---
        
        # Identificamos los work.entry.type que generan sobre-costos
        surcharge_types = ['HE25', 'HEN25', 'HE35', 'HEN35', 'FERIADO']
        surcharge_work_entries = self.env['hr.work.entry'].search([
            #('payslip_id', '=', self.id),
            ('work_entry_type_id.code', 'in', surcharge_types),
            ('date_start', '<=', self.date_to),
            ('date_stop', '>=', self.date_from)
        ])

        for entry in surcharge_work_entries:
            # Calcular el SOBRE-COSTO de esta entrada de trabajo
            surcharge_rate = 0.0
            if entry.work_entry_type_id.code in ['HE25', 'HEN25']: surcharge_rate += 0.25
            if entry.work_entry_type_id.code in ['HE35', 'HEN35']: surcharge_rate += 0.35
            if entry.work_entry_type_id.code in ['HEN25', 'HEN35']: surcharge_rate += 0.35 # Asumiendo recargo nocturno
            if entry.work_entry_type_id.code == 'FERIADO': surcharge_rate += 1.0
            
            premium_cost = entry.duration * hourly_wage * surcharge_rate

            # Distribuir este sobre-costo entre las hojas de horas que se cruzan en el tiempo
            overlapping_timesheets = timesheets.filtered(
                lambda t: t.date == entry.date_start.date() # Simplificación, una lógica real compararía horas
            )
            # Por simplicidad, asignamos todo el sobre-costo a la primera cuenta analítica encontrada
            if overlapping_timesheets:
                analytic_account = overlapping_timesheets[0].account_id
                costs_by_analytic[analytic_account]['SCTR_RECARGO'] += premium_cost
        
        # --- PASO 2: PRORRATEO DE COSTOS BASE ---

        # 1. Calcular el total de costos base (Costo Total - Sobre-Costos ya asignados)
        total_company_cost = sum(all_cost_lines.mapped('total'))
        total_premium_cost_assigned = sum(v['SCTR_RECARGO'] for v in costs_by_analytic.values())
        total_base_cost = total_company_cost - total_premium_cost_assigned

        # 2. Calcular horas regulares para el prorrateo
        regular_timesheets = timesheets.filtered(
            lambda t: not any(
                t.date == e.date_start.date() and e.work_entry_type_id.code in surcharge_types
                for e in surcharge_work_entries
            )
        )
        total_regular_hours = sum(regular_timesheets.mapped('unit_amount'))
        if not total_regular_hours: total_regular_hours = 1 # Evitar división por cero

        # 3. Calcular porcentajes de distribución para los costos base
        regular_hours_by_analytic = defaultdict(float)
        for line in regular_timesheets:
            regular_hours_by_analytic[line.account_id] += line.unit_amount
        
        # 4. Distribuir los costos base
        for analytic_account, hours in regular_hours_by_analytic.items():
            percentage = hours / total_regular_hours
            costs_by_analytic[analytic_account]['SCTR_BASE'] += total_base_cost * percentage

        # --- PASO 3: CREAR LOS REGISTROS FINALES ---
        analytic_cost_vals = []
        for analytic_account, costs in costs_by_analytic.items():
            total_distributed_amount = sum(costs.values())
            if total_distributed_amount > 0:
                # Aquí creamos una sola línea por centro de costo. Podríamos crear una por concepto si fuera necesario.
                analytic_cost_vals.append({
                    'payslip_id': self.id,
                    #'salary_rule_id': self.env.ref('hr_payroll.hr_salary_rule_net').id, # Placeholder
                    'salary_rule_id': self.env.ref('mstech_payroll_extend.rule_net_pe').id, # Placeholder
                    'analytic_account_id': analytic_account.id,
                    'amount': total_distributed_amount,
                })
        
        if analytic_cost_vals:
            self.env['hr.payslip.analytic.cost'].create(analytic_cost_vals)