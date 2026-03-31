from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)


class HrBonusConfig(models.Model):
    _name = 'hr.bonus.config'
    _description = 'Configuración de Plantilla de Bonos'

    name = fields.Char(string='Nombre de la Plantilla', required=True, help="Ej: Bono por Productividad Mensual")
    active = fields.Boolean(default=True)
    
    # --- CAMPOS PARA LA NÓMINA (CORREGIDOS) ---
    payslip_description = fields.Char(
        string="Descripción en Nómina",
        required=True,
        help="El texto que aparecerá en la línea de la boleta de pago. Ej: 'Bono de Productividad'"
    )
    payslip_code = fields.Char(
        string="Código en Nómina",
        readonly=True, default='BONO',
        help="El código técnico que usarán las reglas salariales. Ej: 'BONO_PROD'"
    )

    # --- CAMPOS PARA EL CÁLCULO DEL MONTO ---
    bonus_type = fields.Selection([
        ('fixed', 'Monto Fijo'),
        ('variable', 'Cálculo Dinámico (Python)'),
    ], string="Tipo de Cálculo", required=True, default='fixed')

    amount_fixed = fields.Monetary(
        string="Monto Fijo", 
        currency_field='company_currency_id',
        help="Usar si el tipo de cálculo es 'Monto Fijo'."
    )
    code_executor_id = fields.Many2one(
        'python.code.execute',  # El nombre técnico de tu modelo
        string="Script de Cálculo",
        help="Selecciona el script pre-configurado para calcular el monto del bono. "
             "El script debe retornar un valor numérico."
    )

    # --- CAMPOS PARA AUTOMATIZACIÓN ---
    recurrence = fields.Selection([
        ('manual', 'Manual'),
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('yearly', 'Anual'),
    ], string="Recurrencia", default='manual', required=True)

    # ➤ NUEVO CAMPO: FECHA DE CORTE
    # Para el cron, será la fecha en que se ejecuta. Para el manual, el usuario la define.
    # También la podemos usar como 'próxima fecha de ejecución' para el cron.
    next_execution_date = fields.Date(
        string="Próxima Fecha de Ejecución/Corte",
        default=fields.Date.context_today,
        help="Fecha en que se evaluará la condición del bono. Se actualiza automáticamente para bonos recurrentes."
    )

    bonus_ids = fields.One2many(
        'hr.bonus', 
        'config_id', 
        string="Bonos Generados",
        readonly=True
    )
    bonuses_count = fields.Integer(compute='_compute_bonuses_count', string="Nº Bonos")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.constrains('payslip_code')
    def _check_payslip_code(self):
        for record in self:
            if not record.payslip_code or not record.payslip_code.isidentifier():
                raise ValidationError(_("El código en nómina debe ser un identificador válido de Python (letras, números, guion bajo, sin espacios)."))

    @api.depends('bonus_ids')
    def _compute_bonuses_count(self):
        for record in self:
            record.bonuses_count = len(record.bonus_ids)

    def _get_amount(self, employee):
        self.ensure_one()
        amount = 0.0

        # --- Lógica para Bono Fijo ---
        if self.bonus_type == 'fixed':
            amount = self.amount_fixed

        # --- Lógica para Bono Variable ---
        elif self.bonus_type == 'variable' and self.code_executor_id:
            script = self.code_executor_id

            # ➤ NUEVA VALIDACIÓN: Comprobamos si el script está verificado
            if script.code_state != 'done':
                # Lanzamos un error que detendrá el cron y será visible en los logs.
                # Esto es una medida de seguridad para forzar la configuración correcta.
                raise ValidationError(
                    f"El script de cálculo '{script.code_name}' asociado a la plantilla de bono '{self.name}' no está en estado 'verified'. "
                    "La generación de bonos se ha detenido. Por favor, verifique el script para continuar."
                )

            try:
                # Pasamos el contexto del empleado al script.
                # Asumo que tu método puede recibir el registro como argumento.
                # Si no, ajusta esta línea a: script.with_context(active_id=employee.id).action_execute_code()

                script.with_context(bonus_context={'employee': employee}).action_execute_code()

                # Recuperamos el resultado del campo 'code_result'.
                result_str = script.code_result
                if result_str:
                    amount = float(result_str)

            except Exception as e:
                _logger.error(
                    f"Error al ejecutar script '{script.code_name}' para el bono '{self.name}' "
                    f"y empleado '{employee.name}': {e}"
                )
                return
        return amount

    # =========================================================================
    # =========================================================================
    @api.model
    def _cron_generate_bonuses(self):
        """
        Este método, llamado por un cron diario, busca plantillas de bonos automáticos
        cuya fecha de ejecución sea hoy, valida, ejecuta los scripts, genera los
        bonos correspondientes y programa la siguiente ejecución.
        """
        today = fields.Date.today()
        
        configs_to_run = self.search([
            ('recurrence', '!=', 'manual'),
            ('active', '=', True),
            ('next_execution_date', '=', today)
        ])
        
        _logger.info(f"CRON Bonos: Se encontraron {len(configs_to_run)} plantillas de bonos para ejecutar hoy ({today}).")

        for config in configs_to_run:
            employees = self.env['hr.employee'].search([('contract_id.state', '=', 'open')])

            for employee in employees:
                amount = config._get_amount(employee)

                if amount and amount > 0:
                    self.env['hr.bonus'].create({
                        'employee_id': employee.id,
                        'config_id': config.id,
                        'amount': amount,
                        'date': today,
                    })
            
            # Reprogramamos la siguiente ejecución
            next_date = None
            if config.recurrence == 'monthly':
                next_date = today + relativedelta(months=1)
            elif config.recurrence == 'quarterly':
                next_date = today + relativedelta(months=3)
            elif config.recurrence == 'yearly':
                next_date = today + relativedelta(years=1)
            
            if next_date:
                config.write({'next_execution_date': next_date})
                _logger.info(f"Bono '{config.name}' reprogramado para el {next_date}.")

        _logger.info("CRON Bonos: Finalizada la ejecución de generación de bonos.")
        return True