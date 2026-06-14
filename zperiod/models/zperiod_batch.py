# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ZPeriodBatch(models.Model):
    _name = "zperiod.batch"
    _description = "Generador en Lote de Períodos"
    _inherit = ["mail.thread"]
    _order = "date_start desc"

    name = fields.Char(string="Nombre del Lote", required=True)
    date_start = fields.Date(string="Fecha Inicio", required=True)
    date_end = fields.Date(string="Fecha Fin", required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)

    period_ids = fields.One2many("zperiod", "batch_id", string="Períodos Generados")

      # Estado del lote
    state = fields.Selection([("draft", "Borrador"),
                    ("generated", "Generado")], string="Estado", default="draft", tracking=True)
    
    
        
    #############MEtodo pra generar periodos
    
    def action_generate_periods(self):
        """Genera períodos individuales solo para empleados activos con contratos activos"""
        Employee = self.env['hr.employee']
        Period = self.env['zperiod']
        Contract = self.env['hr.contract']

        # Buscar empleados activos en la compañía
        employees = Employee.search([('company_id', '=', self.company_id.id), ('active', '=', True)])
        created_count = 0

        for emp in employees:
            # Verificar si tiene al menos un contrato abierto
            active_contract = Contract.search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'open')
            ], limit=1)
            if not active_contract:
                continue  # saltar empleado sin contrato activo

            # Verificar si ya existe el período para evitar duplicados
            exists = Period.search([
                ('employee_id', '=', emp.id),
                ('date_start', '=', self.date_start),
                ('date_end', '=', self.date_end)
            ])
            if not exists:
                # Crear período; el name se genera automáticamente en ZPeriod.create()
                Period.create({
                    'employee_id': emp.id,
                    'batch_id': self.id,
                    'date_start': self.date_start,
                    'date_end': self.date_end,
                    'company_id': self.company_id.id,
                    'state': 'open',
                })
                created_count += 1

        # Cambiar el estado del lote a 'generated'
        self.state = 'generated'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Generación Completa',
                'message': f'Se han generado {created_count} períodos en estado borrador.',
                'type': 'success',
            }
        }
    
    
    ### ACtualziacion masiva de asistnecia en los epridodos generados
    def action_actualizar_periodos(self):
        self.ensure_one()

        periods = self.period_ids.filtered(lambda p: p.state != 'cancel')

        if not periods:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin períodos',
                    'message': 'No hay períodos generados para actualizar.',
                    'type': 'warning',
                }
            }

        periods.with_context(
            tracking_disable=True,
            mail_notrack=True,
        ).action_actualizar()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Actualización Completa',
                'message': f'Se actualizaron {len(periods)} períodos correctamente.',
                'type': 'success',
            }
        }