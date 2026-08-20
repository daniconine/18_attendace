from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import timedelta

#parametros creados para el calculo denomina
class ZPayrollParameters(models.Model):
    _name = 'zpayroll.parameters'
    _description = 'Parámetros de Nómina'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(string='Nombre',compute='_compute_name',store=True)
    uit = fields.Float(string='UIT',tracking=True)
    rmv = fields.Float(string='RMV',tracking=True)
    rma = fields.Float(string='RMA',tracking=True)
    onp_rate = fields.Float(string='% ONP',tracking=True)
    essalud_rate = fields.Float(string='% EsSalud',tracking=True)
    eps_rate = fields.Float(string='% EPS Solidario',tracking=True)
    eps_essalud_rate = fields.Float(string='% EPS_EsSalud',tracking=True)
    
    date_from = fields.Date(string='Vigente desde',required=True,tracking=True)
    date_to = fields.Date(string='Vigente hasta',tracking=True)

    #Nombre automatico
    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for record in self:
            if not record.date_from:
                record.name = 'Parámetros de Nómina'
                continue

            date_from = record.date_from.strftime('%d/%m/%Y')

            if record.date_to:
                date_to = record.date_to.strftime('%d/%m/%Y')
                record.name = f'Parámetros de Nómina {date_from} - {date_to}'
            else:
                record.name = f'Parámetros de Nómina {date_from} - Activo'
        
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError(
                        'La fecha "Vigente hasta" no puede ser menor '
                        'que la fecha "Vigente desde".'
                    )

    @api.constrains('date_from', 'date_to')
    def _check_overlapping_periods(self):
        for record in self:
            if not record.date_from:
                continue

            domain = [
                ('id', '!=', record.id),
                '|',
                ('date_to', '=', False),
                ('date_to', '>=', record.date_from),
            ]

            if record.date_to:
                domain.append(('date_from', '<=', record.date_to))

            overlapping = self.search(domain, limit=1)

            if overlapping:
                raise ValidationError(
                    'El rango de vigencia se superpone con el registro "%s".'
                    % overlapping.display_name
                )
    
    

    def copy(self, default=None):
        self.ensure_one()

        if not self.date_to:
            raise ValidationError(
                'Debe cerrar la vigencia del registro antes de duplicarlo.'
            )

        default = dict(default or {})
        default.update({
            'date_from': self.date_to + timedelta(days=1),
            'date_to': False,
        })

        return super().copy(default)