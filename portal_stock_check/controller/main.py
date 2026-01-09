from odoo import http
from odoo.http import request

class PortalController(http.Controller):
    @http.route('/my/text_display', type='http', auth="user", website=True)
    def portal_text(self, **kw):
        # Definir el texto que queremos mostrar
        text_data = {
            'text': '¡Este es un texto estático mostrado en el portal de Odoo!'
        }
        # Renderiza la vista con los datos que pasamos
        return request.render('portal_stock_check.portal_text_template', text_data)
