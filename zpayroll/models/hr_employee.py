from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from odoo.modules.module import get_module_root

class HrLaborRegimePE(models.Model):
    _name = 'hr.labor.regime.pe'
    _description = 'Régimen Laboral (Perú)'
    _order = 'name'

    name = fields.Char(string='Nombre del Régimen', required=True)
    code = fields.Char(string='Código', help="Código interno o del decreto ley, ej: 728, MYPE")
    plame_code = fields.Char(string='Código en PLAME')
    annual_vacation_days = fields.Integer(
        string='Días de Vacaciones Anuales',
        required=True,
        default=0,
        help="Número de días de vacaciones que un empleado gana al cumplir un año de servicio bajo este régimen."
    )
    active = fields.Boolean(default=True)
    receives_gratification = fields.Boolean(string="Recibe gratificaciones", default=True)
    
    
    


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    zemployee_extension_id = fields.Many2one(
        'zemployee.extension',
        string='Extensión Perú',
        compute='_compute_zemployee_extension_id',
        store=False
    )

    def _compute_zemployee_extension_id(self):
        for emp in self:
            emp.zemployee_extension_id = self.env['zemployee.extension'].search(
                [('employee_id', '=', emp.id)],
                limit=1
            )

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)

        Extension = self.env['zemployee.extension']
        for emp in employees:
            existing = Extension.search([('employee_id', '=', emp.id)], limit=1)
            if not existing:
                Extension.create({
                    'employee_id': emp.id,
                })

        return employees
    
    # Método que usa la nómina para saber si tiene derecho a asignación familiar
    def has_family_allowance(self):
        self.ensure_one()

        extension = self.zemployee_extension_id
        if not extension:
            return False

        today = fields.Date.today()

        for fam in extension.family_ids:
            if fam.relationship != 'child':
                continue

            if fam.is_disabled:
                return True

            if fam.birth_date:
                age = (
                    today.year
                    - fam.birth_date.year
                    - ((today.month, today.day) < (fam.birth_date.month, fam.birth_date.day))
                )

                if age < 18:
                    return True

                if fam.is_student and age <= 24:
                    return True

        return False