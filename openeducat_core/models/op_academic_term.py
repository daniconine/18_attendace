# -*- coding: utf-8 -*-
# Part of OpenEduCat. See LICENSE file for full copyright & licensing details.

##############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import ValidationError  # Importar ValidationError


class OpAcademicTerm(models.Model):
    _name = 'op.academic.term'
    _description = 'Periodo Academico'
    _order = 'term_start_date'

    name = fields.Char(string='Nombre Periodo', required=True)
    term_start_date = fields.Date(string='Fecha Inicio', required=True)
    term_end_date = fields.Date(string='Fecha Finalizacion', required=True)
    term_lective = fields.Selection(selection=[
        ('0','No Defenido'),
        ('1','Semestral'),
        ('2','Anual'),
    ], default='1', string='Periodo Lectivo')
    term_type = fields.Selection(selection=[
        ('0','No Defenido'),
        ('1','Regular'),
    ], default='1', string='Tipo Periodo')
    
    academic_year_id = fields.Many2one(
        'op.academic.year', 
        string='Año Academico', 
        required=True,
        ondelete='cascade')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id)
    
    @api.constrains('term_start_date', 'term_end_date')
    def _check_term_dates(self):
        for record in self:
            if record.term_start_date >= record.term_end_date:
                raise ValidationError('La fecha de inicio del período debe ser anterior a la fecha de finalización.')
            if record.academic_year_id:
                if record.term_start_date < record.academic_year_id.start_date or record.term_end_date > record.academic_year_id.end_date:
                    raise ValidationError('Las fechas del período deben estar dentro del año académico.')
