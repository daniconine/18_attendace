from odoo import models, fields, api

class ZLeaveDashboard(models.Model):
    _name = 'zleave.dashboard'
    _description = 'Tablero ZLeave'

    name = fields.Char(string="Título", required=True)
    description = fields.Text(string="Descripción")
    icon = fields.Char(string="Icono", default="fa-star")
    action_id = fields.Many2one('ir.actions.act_window', string="Acción")
    groups_id = fields.Many2many('res.groups', string="Grupos permitidos")
    
    def action_open_target(self):
        self.ensure_one()
        if self.action_id:
            # Usamos .sudo() para saltar el error de acceso a ir.actions.act_window
            action = self.action_id.sudo().read()[0]
            
            # Opcional: Si quieres forzar que siempre se abra en modo lista
            action['views'] = [(False, 'list'), (False, 'form')]
            return action
        return False