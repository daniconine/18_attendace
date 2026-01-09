from odoo import http
from odoo.http import request

class PortalController(http.Controller):
    @http.route('/my/text_display', type='http', auth="user", website=True)
    def portal_text(self, **kw):
        # Pasamos un texto al frontend
        text_data = {
            'text': '¡Hola desde Odoo! Este es un texto mostrado con JavaScript.'
        }
        return request.render('my_module.portal_text_template', text_data)
