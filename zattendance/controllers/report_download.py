import json
import urllib.parse

from odoo import http
from odoo.http import request, content_disposition
from odoo.addons.web.controllers.report import ReportController


class ZAttendanceReportController(ReportController):

    @http.route("/report/download", type="http", auth="user")
    def report_download(self, data, context=None, token=None):
        request_content = json.loads(data)
        url = request_content[0]
        report_type = request_content[1]

        if report_type != "xlsx":
            return super().report_download(data, context=context, token=token)

        filename = None

        parsed_url = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed_url.query)

        if query.get("options"):
            options = json.loads(query["options"][0])
            filename = options.get("xlsx_filename")

        response = super().report_download(data, context=context, token=token)

        if filename:
            if not filename.lower().endswith(".xlsx"):
                filename = "%s.xlsx" % filename

            response.headers["Content-Disposition"] = content_disposition(filename)

        return response