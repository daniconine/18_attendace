# mstech_payroll_extend/models/commission_config.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

import logging

_logger = logging.getLogger(__name__)

class HrCommissionConfig(models.Model):
    _name = 'hr.commission.config'
    _description = 'Configuración de Plan de Comisiones Dinámico'

    name = fields.Char(string='Nombre del Plan de Comisión', required=True)
    active = fields.Boolean(string="Activo", default=False, copy=False)

    # --- DEFINICIÓN DEL ORIGEN (DESACOPLADO) ---
    model_id = fields.Many2one('ir.model', string="Modelo de Origen", ondelete="cascade", required=True)
    model_name = fields.Char(related='model_id.model', string="Nombre Técnico del Modelo", readonly=True)
    domain = fields.Char(string="Dominio de Aplicación", default="[]")

    # --- MAPEO DE CAMPOS (NOMBRES TÉCNICOS) ---
    employee_field_name = fields.Char(string="Campo del Empleado", required=True, help="Ej: user_id.employee_id")
    amount_base_field_name = fields.Char(string="Campo del Monto Base", required=True, help="Ej: amount_untaxed")
    currency_field_name = fields.Char(string="Campo de la Moneda", required=True, help="Ej: currency_id")
    date_field_name = fields.Char(string="Campo de la Fecha", required=True, help="Ej: invoice_date")

    # --- LÓGICA DE CÁLCULO ---
    code_executor_id = fields.Many2one('python.code.execute', string="Script de Cálculo", required=True)
    
    # --- RESULTADO EN NÓMINA ---
    payslip_description = fields.Char(string="Descripción en Nómina", required=True)
    payslip_code = fields.Char(string="Código en Nómina", readonly=True, default='COMISIONES')

    # --- AUTOMATIZACIÓN (Tus 3 Hooks) ---
    action_create_id = fields.Many2one('ir.actions.server', copy=False)
    action_update_id = fields.Many2one('ir.actions.server', copy=False)
    action_unlink_id = fields.Many2one('ir.actions.server', copy=False)
    automation_create_id = fields.Many2one('base.automation', copy=False)
    automation_update_id = fields.Many2one('base.automation', copy=False)
    automation_unlink_id = fields.Many2one('base.automation', copy=False)

    # --- CÓDIGO PYTHON PARA LAS ACCIONES ---
    python_code = fields.Text(
        string='Código Python para Acción',
        default="""# Código autogenerado para disparar la lógica de comisiones.
# 'records' contiene el/los registros que activaron la acción.
config = env['hr.commission.config'].search([
    ('model_id.model', '=', records._name),
    ('active', '=', True)
], limit=1)
if config:
    config._process_commission_for_record(records)
""",
        readonly=True, copy=False
    )
    
    # --- Botones y Lógica de Activación (Tu Patrón) ---
    def activate_plan(self):
        for config in self:
            other_active = self.search([('id', '!=', config.id), ('model_id', '=', config.model_id.id), ('active', '=', True)])
            if other_active:
                raise UserError(_("Ya existe otra configuración activa para el modelo '%s'.") % config.model_id.name)
            
            def ensure_automation(trigger, action_field, automation_field, suffix):
                server_action = getattr(config, action_field)
                if not server_action:
                    server_action = self.env['ir.actions.server'].create({
                        'name': f'Comisión ({suffix}) - {config.name}',
                        'model_id': config.model_id.id, 'state': 'code', 'code': config.python_code,
                    })
                    config[action_field] = server_action.id
                
                automation = getattr(config, automation_field)
                if not automation:
                    automation = self.env['base.automation'].create({
                        'name': f'Auto-Comisión ({suffix}) - {config.name}',
                        'model_id': config.model_id.id, 'trigger': trigger, 'action_server_ids': [fields.Command.link(server_action.id)],
                    })
                    config[automation_field] = automation.id
                automation.active = True

            ensure_automation('on_create', 'action_create_id', 'automation_create_id', 'Crear')
            ensure_automation('on_write', 'action_update_id', 'automation_update_id', 'Actualizar')
            ensure_automation('on_unlink', 'action_unlink_id', 'automation_unlink_id', 'Eliminar')
            config.active = True

    def deactivate_plan(self):
        for config in self:
            if config.automation_create_id: config.automation_create_id.active = False
            if config.automation_update_id: config.automation_update_id.active = False
            if config.automation_unlink_id: config.automation_unlink_id.active = False
            config.active = False


    def _process_commission_for_record(self, records):
        self.ensure_one()
        event_type = self.env.context.get('automated_action_trigger', 'on_write')

        for record in records:
            # Buscamos si ya existe una comisión para este registro
            existing_commission = self.env['hr.commission'].search([
                ('res_model', '=', record._name), ('res_id', '=', record.id)
            ], limit=1)

            # --- Lógica de Eliminación ---
            domain = safe_eval(self.domain or '[]')
            is_valid_now = record.filtered_domain(domain)
            if event_type == 'on_unlink' or not is_valid_now:
                if existing_commission:
                    if existing_commission.state == 'draft':
                        existing_commission.unlink()
                    else:
                        _logger.warning(f"Se intentó eliminar la comisión para {record.display_name} pero ya está liquidada.")
                continue

            # --- Lógica de Creación/Actualización ---
            def eval_expr(expr):
                # Tu helper para evaluar expresiones de forma segura
                if not expr: return None
                try:
                    return safe_eval(expr, {'record': record, 'env': self.env})
                except Exception as e:
                    _logger.error(f"Error evaluando la expresión '{expr}': {e}")
                    return None

            employee = eval_expr(self.employee_field_name)
            if not employee: continue # Si no se puede determinar el empleado, saltamos

            # Extraer valores y manejar tipo de cambio
            source_amount = eval_expr(self.amount_base_field_name) or 0.0
            source_currency = eval_expr(self.currency_field_name)
            commission_date = eval_expr(self.date_field_name) or fields.Date.today()
            company_currency = self.env.company.currency_id

            # ➤ CORRECCIÓN: Cálculo y almacenamiento de la Tasa de Cambio
            exchange_rate = 1.0
            amount_in_company_currency = source_amount
            if source_currency and source_currency != company_currency:
                exchange_rate = self.env['res.currency']._get_conversion_rate(
                    source_currency, company_currency, self.env.company, commission_date
                )
                amount_in_company_currency = source_amount * exchange_rate

            script = self.code_executor_id
            # Ejecutar script de cálculo
            if script.code_state != 'done':
                raise ValidationError(
                    _("El script de cálculo '%s' para el plan de comisión '%s' no está verificado. La operación se ha detenido.") % 
                    (script.code_name, self.name)
                )
            
            # Asumiendo que tu script puede usar un contexto
            context_for_script = {'record': record, 'employee': employee, 'base_amount': amount_in_company_currency}
            script.with_context(commission_context=context_for_script).action_execute_code()
            commission_amount = float(script.code_result or 0.0)

            if commission_amount > 0:
                vals = {
                    'config_id': self.id,
                    'employee_id': employee.id,
                    'amount': commission_amount,
                    'date': commission_date,
                    'res_model': record._name,
                    'res_id': record.id,
                    'source_amount': source_amount,          # Guardamos el monto original
                    'source_currency_id': source_currency.id if source_currency else None, # y su moneda
                    'exchange_rate': exchange_rate,         # <-- ¡Y AHORA LA TASA DE CAMBIO!
                }
                
                existing_commission = self.env['hr.commission'].search([
                    ('res_model', '=', record._name), ('res_id', '=', record.id)
                ], limit=1)

                if existing_commission:
                    if existing_commission.state == 'draft':
                        existing_commission.write(vals)
                else:
                    self.env['hr.commission'].create(vals)