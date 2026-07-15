from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ZPayrollReportRuleSalaryWizard(models.TransientModel):
    _name = "zpayroll.report.rule.salary.wizard"
    _description = "Wizard Reporte de Regla Salarial"

    payroll_year = fields.Char(
        string="Año",
        required=True,
        default=lambda self: str(fields.Date.today().year),
    )

    payroll_month_from = fields.Selection([
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
    ], string="Mes desde", required=True)

    payroll_month_to = fields.Selection([
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
    ], string="Mes hasta", required=True)

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

    salary_rule_id = fields.Many2one(
        "hr.salary.rule",
        string="Regla salarial",
        required=True,
        domain=[("active", "=", True)],
    )

    include_zero = fields.Boolean(
        string="Incluir trabajadores sin monto",
        default=False,
    )

    @api.onchange("company_id")
    def _onchange_company_id(self):
        self.employee_ids = [(5, 0, 0)]

    def action_print_xlsx(self):
        self.ensure_one()

        month_from = int(self.payroll_month_from)
        month_to = int(self.payroll_month_to)

        if month_from > month_to:
            raise UserError(_("El mes desde no puede ser mayor que el mes hasta."))

        if self.employee_selection == "specific" and not self.employee_ids:
            raise UserError(_("Debe seleccionar al menos un trabajador."))

        data = {
            "payroll_year": self.payroll_year,
            "payroll_month_from": self.payroll_month_from,
            "payroll_month_to": self.payroll_month_to,
            "company_id": self.company_id.id,
            "employee_selection": self.employee_selection,
            "employee_ids": self.employee_ids.ids,
            "salary_rule_id": self.salary_rule_id.id,
            "include_zero": self.include_zero,
        }

        return self.env.ref(
            "zpayroll.action_report_rule_salary_xlsx"
        ).report_action(self, data=data)