from odoo import models, fields


class ZPayrollReportWizard(models.TransientModel):
    _name = "zpayroll.report.wizard"
    _description = "Wizard Reporte Mensual de Planilla"

    payroll_month = fields.Selection([
        ("01", "ENERO"),
        ("02", "FEBRERO"),
        ("03", "MARZO"),
        ("04", "ABRIL"),
        ("05", "MAYO"),
        ("06", "JUNIO"),
        ("07", "JULIO"),
        ("08", "AGOSTO"),
        ("09", "SEPTIEMBRE"),
        ("10", "OCTUBRE"),
        ("11", "NOVIEMBRE"),
        ("12", "DICIEMBRE"),
    ], string="Mes", required=True)

    payroll_year = fields.Char(
        string="Año",
        required=True,
        default=lambda self: str(fields.Date.today().year),
    )

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    employee_selection = fields.Selection([
        ("all", "Todos los trabajadores"),
        ("specific", "Trabajadores específicos"),
    ], string="Trabajadores", default="all", required=True)

    employee_ids = fields.Many2many(
        "hr.employee",
        string="Trabajadores",
    )

    def action_print_xlsx(self):
        self.ensure_one()

        data = {
            "payroll_month": self.payroll_month,
            "payroll_year": self.payroll_year,
            "company_id": self.company_id.id,
            "employee_selection": self.employee_selection,
            "employee_ids": self.employee_ids.ids,
        }

        return self.env.ref(
            "zpayroll.action_report_payroll_monthly_xlsx"
        ).report_action(self, data=data)