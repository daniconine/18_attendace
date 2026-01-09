# -*- coding: utf-8 -*-
###############################################################################
#Este campo esta relacionado con estudiante, esta en la vista form de estudainte
# #quizas sea posible utilizarlo para estado de matriculado, terminado o jalado.
#
###############################################################################

from odoo import models, fields


class OpCategory(models.Model):
    _name = "op.category"
    _description = "OpenEduCat Category"

    name = fields.Char('Name', size=256, required=True)
    code = fields.Char('Code', size=16, required=True)

    _sql_constraints = [
        ('unique_category_code',
         'unique(code)', 'Code should be unique per category!')]
