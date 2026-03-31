# mstech_payroll_extend/models/payslip_run.py

import base64
from odoo import models, fields, api, _

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    # Campo para seleccionar los reportes regulatorios a generar
    regulatory_report_template_ids = fields.Many2many(
        'hr.report.template',
        'payslip_run_report_template_rel',
        'run_id', 'template_id',
        string="Reportes Regulatorios a Generar",
        domain="[('is_bank_payment', '=', False)]" # Dominio para no mezclar con pagos
    )

    # Campo para ver los resultados
    generated_file_ids = fields.One2many(
        'hr.report.file', 
        'payslip_run_id', 
        string="Archivos Generados"
    )

    date_cutoff_overtime = fields.Date(string="Fecha de Corte para Horas Extras")
    date_cutoff_leaves = fields.Date(string="Fecha de Corte para Ausencias")
    date_cutoff_bonuses = fields.Date(string="Fecha de Corte para Bonos")
    date_cutoff_commissions = fields.Date(string="Fecha de Corte para Comisiones")

    pending_overtime_ids = fields.One2many(
        'hr.overtime.request',
        compute='_compute_pending_incidents',
        string="Horas Extras Pendientes de Aprobación"
    )
    pending_leave_ids = fields.One2many(
        'hr.leave',
        compute='_compute_pending_incidents',
        string="Ausencias Pendientes de Aprobación"
    )
    # Para bonos y comisiones, asumimos que solo los 'borrador' están pendientes.
    pending_bonus_ids = fields.One2many(
        'hr.bonus',
        compute='_compute_pending_incidents',
        string="Bonos Pendientes (Borrador)"
    )
    pending_commission_ids = fields.One2many(
        'hr.commission',
        compute='_compute_pending_incidents',
        string="Comisiones Pendientes (Borrador)"
    )

    is_analytic_distribution_enabled = fields.Boolean(
        compute='_compute_is_analytic_distribution_enabled'
    )

    company_id = fields.Many2one(string="Compañía", comodel_name="res.company", default=lambda self: self.env.company)

    @api.depends('company_id.enable_payroll_analytic_distribution')
    def _compute_is_analytic_distribution_enabled(self):
        for run in self:
            run.is_analytic_distribution_enabled = run.company_id.enable_payroll_analytic_distribution

    @api.depends('date_start', 'date_end')
    def _compute_pending_incidents(self):
        for run in self:
            if not run.date_start or not run.date_end:
                run.pending_overtime_ids = run.pending_leave_ids = run.pending_bonus_ids = run.pending_commission_ids = False
                continue
            
            # Usar las fechas de corte si están definidas, si no, usar las del lote.
            date_to_overtime = run.date_cutoff_overtime or run.date_end
            date_to_leaves = run.date_cutoff_leaves or run.date_end
            date_to_bonuses = run.date_cutoff_bonuses or run.date_end
            date_to_commissions = run.date_cutoff_commissions or run.date_end

            run.pending_overtime_ids = self.env['hr.overtime.request'].search([('start_datetime', '<=', date_to_overtime), ('state', 'in', ['draft', 'submitted'])])
            run.pending_leave_ids = self.env['hr.leave'].search([('request_date_to', '<=', date_to_leaves), ('state', '=', 'confirm')])
            run.pending_bonus_ids = self.env['hr.bonus'].search([('date', '<=', date_to_bonuses), ('state', '=', 'draft')])
            run.pending_commission_ids = self.env['hr.commission'].search([('date', '<=', date_to_commissions), ('state', '=', 'draft')])
    
    def action_view_analytic_distribution(self):
        self.ensure_one()
        
        # Buscamos los IDs de todas las líneas de costo analítico de este lote
        analytic_line_ids = self.slip_ids.mapped('analytic_cost_line_ids').ids
        
        # Devolvemos una acción que abre una nueva vista con estos registros
        return {
            'type': 'ir.actions.act_window',
            'name': f'Distribución de Costo Analítico para {self.name}',
            'res_model': 'hr.payslip.analytic.cost',
            'view_mode': 'list,pivot,graph', # Permitimos múltiples vistas
            'domain': [('id', 'in', analytic_line_ids)],
            'target': 'current',
        }
    
    def action_add_active_employees(self):
        """Añade todos los empleados con contrato activo al lote de nóminas."""
        self.ensure_one()
        active_employees = self.env['hr.employee'].search([('contract_id.state', '=', 'open')])
        existing_employees = self.slip_ids.mapped('employee_id')
        employees_to_add = active_employees - existing_employees
        
        payslips_to_create = []
        for employee in employees_to_add:
            slip_data = self.env['hr.payslip']._get_default_slip_data(employee, self.date_start, self.date_end, self)
            payslips_to_create.append(slip_data)
        
        if payslips_to_create:
            self.env['hr.payslip'].create(payslips_to_create)
    
    # Heredamos el botón de cierre del lote
    #def action_close(self):
    #    res = super().action_close()
    def close_payslip_run(self):
        res = super().close_payslip_run()
        self.generate_all_reports()
        return res

    # --- NUESTRO MÉTODO ORQUESTADOR ---
    def generate_all_reports(self):
        self.ensure_one()

        # 1. Generar Archivos de Pago Masivo por Banco
        # Agrupamos las nóminas por el banco definido en el contrato
        slips_by_bank = {}
        for slip in self.slip_ids.filtered(lambda s: s.state == 'done' and s.contract_id.bank_id):
            bank = slip.contract_id.bank_id
            if bank not in slips_by_bank:
                slips_by_bank[bank] = self.env['hr.payslip']
            slips_by_bank[bank] |= slip
        
        for bank, slips in slips_by_bank.items():
            if bank.payment_file_template_id:
                self.env['hr.report.template']._generate_report_from_template(
                    bank.payment_file_template_id,
                    slips,
                    self
                )
        
        # 2. Generar Reportes Regulatorios seleccionados
        self.generated_file_ids.unlink()
        for template in self.regulatory_report_template_ids:
            self.env['hr.report.template']._generate_report_from_template(
                template,
                self.slip_ids.filtered(lambda s: s.state == 'done'),
                self
            )

        return True