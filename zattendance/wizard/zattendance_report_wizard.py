from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

#### Calse abstracta para crear el reporte

class ZAttendanceReportWizard(models.TransientModel):
    _name = "zattendance.report.wizard"
    _description = "Wizard Reporte XLSX de Asistencia"

    date_from = fields.Date(
        string="Fecha desde",
        required=True,
    )

    date_to = fields.Date(
        string="Fecha hasta",
        required=True,
    )

    employee_selection = fields.Selection(
        selection=[
            ("all", "Todos los empleados"),
            ("specific", "Empleados específicos"),
        ],
        string="Empleados",
        default="all",
        required=True,
    )

    employee_ids = fields.Many2many(
        "hr.employee",
        string="Empleados específicos",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_("La fecha desde no puede ser mayor que la fecha hasta."))

    @api.constrains("employee_selection", "employee_ids")
    def _check_employee_selection(self):
        for wizard in self:
            if wizard.employee_selection == "specific" and not wizard.employee_ids:
                raise ValidationError(_("Debe seleccionar al menos un empleado."))

    
    
    def action_print_xlsx(self):
        self.ensure_one()

        employee_ids = []
        if self.employee_selection == "specific":
            employee_ids = self.employee_ids.ids

        filename = self._get_report_base_filename()

        data = {
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "employee_selection": self.employee_selection,
            "employee_ids": employee_ids,
            "company_id": self.company_id.id,
            "xlsx_filename": filename,
        }

        report = self.env.ref("zattendance.action_report_zattendance_xlsx")
        action = report.report_action(self, data=data)
        action["name"] = filename

        return action


    def _get_report_base_filename(self):
        self.ensure_one()

        selection_label = "Todos"
        if self.employee_selection == "specific":
            selection_label = "Especifico"

        date_from = fields.Date.to_string(self.date_from) if self.date_from else ""
        date_to = fields.Date.to_string(self.date_to) if self.date_to else ""

        return "Reporte de Asistencia %s (%s - %s)" % (
            selection_label,
            date_from,
            date_to,
        )