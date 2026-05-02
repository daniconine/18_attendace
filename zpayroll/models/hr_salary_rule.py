from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    is_remunerative = fields.Boolean(
        string='Remunerativo',
        help='Concepto que tiene naturaleza remunerativa.')

    is_taxable_r5 = fields.Boolean(
        string='Afecto Renta 5ta',
        help='Concepto afecto al cálculo de renta de quinta categoría.')
    
    is_r5_projection_base= fields.Boolean(
        string='Usado en proyectado 5ta',
        help='Concepto usado para proyectar la renta anual de quinta categoría.'
    )   

    is_asegurable = fields.Boolean(
        string='Remuneración Asegurable',
        help='Concepto que forma parte de la base AFP/ONP/EsSalud.')

    is_computable = fields.Boolean(
        string='Computable Beneficios',
        help='Concepto que puede formar parte de la remuneración computable para CTS, vacaciones, gratificación o liquidación.'
    )

    is_variable = fields.Boolean(
        string='Variable',
        help='Concepto variable sujeto a evaluación de regularidad.')

    is_non_taxable = fields.Boolean(
        string='No Afecto',
        help='Concepto no afecto a renta ni aportes.')
    
    