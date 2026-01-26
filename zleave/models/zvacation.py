# models/zvacation.py

from odoo import models, fields, api

class ZVacation(models.Model):
    _name = 'zleave.zvacation'
    _description = 'Solicitud de Vacaciones Personalizadas'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)

    # Tipo de Vacación (Normal o Adelantada)
    vacation_type = fields.Selection([
        ('normal', 'Vacaciones Normales'),
        ('advance', 'Vacaciones Adelantadas'),
    ], string="Tipo de Vacación", required=True)

    date_from = fields.Date(string="Fecha de Inicio", required=True)
    date_to = fields.Date(string="Fecha de Fin", required=True)
    total_days = fields.Integer(string="Total días")
    reason = fields.Text(string="Motivo (Opcional)")

    # Aprobador de la solicitud
    approver_id = fields.Many2one('hr.employee', string="Aprobador", domain="[('job_id.name', '=', 'Manager')]")

    # Estado de la solicitud
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobado'),
        ('refused', 'Rechazado'),
    ], string="Estado", default='draft')

    
   
   
    def action_approve(self):
        self.state = 'approved'

    def action_refuse(self):
        self.state = 'refused'

    
    # Relación Many2many con ZVacationYear
    vacation_year_ids = fields.Many2many(
        'zleave.zvacation.year', 'zvacation_year_rel', 'vacation_id', 'vacation_year_id',
        string='Años de Vacaciones', required=True
    )
    
    @api.model
    def create(self, vals):
        # Filtrar y asignar automáticamente los registros de vacation_year_ids al crear una nueva solicitud
        if 'employee_id' in vals:
            vacation_years = self.env['zleave.zvacation.year'].search([('employee_id', '=', vals['employee_id'])])
            vals['vacation_year_ids'] = [(6, 0, vacation_years.ids)]  # Agregar los registros de vacation_year_ids
        return super(ZVacation, self).create(vals)
    
    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            # Filtrar los registros de vacation_year_ids para el empleado seleccionado
            vacation_years = self.env['zleave.zvacation.year'].search([('employee_id', '=', self.employee_id.id)])
            self.vacation_year_ids = [(6, 0, vacation_years.ids)]