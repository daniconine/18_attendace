# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import str2bool
from odoo import http
from odoo.http import request, route, Stream
from odoo.addons.web.controllers.binary import Binary
from odoo.modules.module import get_module_root

import os
import werkzeug
import logging

_logger = logging.getLogger(__name__)

class BinaryEmpty(Binary):
    
    @route()
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                       filename=None, filename_field='name', mimetype=None, unique=False,
                       download=False, access_token=None, nocache=False):
        try:
            return super().content_common(xmlid, model, id, field, filename, filename_field, mimetype, unique, download, access_token, nocache)
        except werkzeug.exceptions.NotFound:
            if model and id and filename_field and filename and download:
                current_module = os.path.dirname(os.path.abspath(__file__))
                current_module = os.path.basename(get_module_root(current_module))
                stream = Stream.from_path(current_module + '/static/description/empty.txt')
                stream.download_name = filename
                stream.mimetype = 'text/plain'
                send_file_kwargs = {'as_attachment': str2bool(download)}
                return stream.get_response(**send_file_kwargs)
            else:
                raise
