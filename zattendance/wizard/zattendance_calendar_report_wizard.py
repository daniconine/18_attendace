from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


#Wizard del reporte de alendario
class ZAttendanceCalendarReportWizard(models.TransientModel):
    _name = "zattendance.calendar.report.wizard"
    _description = "Wizard Reporte General de Horarios"

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

    @api.constrains("employee_selection", "employee_ids")
    def _check_employee_selection(self):
        for wizard in self:
            if wizard.employee_selection == "specific" and not wizard.employee_ids:
                raise ValidationError(
                    _("Debe seleccionar al menos un empleado.")
                )

    def action_print_calendar_xlsx(self):
        self.ensure_one()

        employee_ids = []
        if self.employee_selection == "specific":
            employee_ids = self.employee_ids.ids

        data = {
            "employee_selection": self.employee_selection,
            "employee_ids": employee_ids,
            "company_id": self.company_id.id,
        }

        return self.env.ref(
            "zattendance.action_report_zattendance_calendar_xlsx"
        ).report_action(self, data=data)