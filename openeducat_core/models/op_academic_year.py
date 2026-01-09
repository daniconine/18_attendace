from odoo import models, fields, api
from odoo.exceptions import ValidationError  # Importar ValidationError

class OpAcademicYear(models.Model):
    _name = 'op.academic.year'
    _description = 'Año Academico'
    _order = 'start_date desc'

    name = fields.Char(string='Año Acdémico', required=True)
    start_date = fields.Date(string='Fecha Inicio', required=True)
    end_date = fields.Date(string='Fecha Finalizacion', required=True)
    academic_term_ids = fields.One2many(
        'op.academic.term', 
        'academic_year_id', 
        string='Periodo Academico'
    )
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id)
    
    _sql_constraints = [
    ('unique_date_range', 
     'CHECK (start_date < end_date)', 
     'La fecha de inicio debe ser anterior a la fecha de finalización.'),
    ('unique_academic_year', 
     'UNIQUE (start_date, end_date)', 
     'Ya existe un año académico con este rango de fechas.')
]
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date >= record.end_date:
                raise ValidationError('La fecha de inicio debe ser anterior a la fecha de finalización.')
