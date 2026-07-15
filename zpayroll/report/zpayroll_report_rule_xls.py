from odoo import models


class ReportZPayrollRuleSalaryXlsx(models.AbstractModel):
    _name = "report.zpayroll.report_rule_salary_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Reporte de Regla Salarial XLSX"

    MONTH_NAMES = {
        1: "ENERO",
        2: "FEBRERO",
        3: "MARZO",
        4: "ABRIL",
        5: "MAYO",
        6: "JUNIO",
        7: "JULIO",
        8: "AGOSTO",
        9: "SEPTIEMBRE",
        10: "OCTUBRE",
        11: "NOVIEMBRE",
        12: "DICIEMBRE",
    }

    def _get_slip_reference(self, slip):
        return (
            slip.number
            or slip.name
            or slip.payslip_nickname
            or ""
        )

    def generate_xlsx_report(self, workbook, data, wizard):
        sheet = workbook.add_worksheet("Regla Salarial")

        title_format = workbook.add_format({
            "bold": True,
            "font_size": 14,
        })

        header_format = workbook.add_format({
            "bold": True,
            "bg_color": "#D9EAF7",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        })

        text_format = workbook.add_format({
            "border": 1,
        })

        money_format = workbook.add_format({
            "num_format": "#,##0.00",
            "border": 1,
        })

        total_format = workbook.add_format({
            "bold": True,
            "border": 1,
            "num_format": "#,##0.00",
        })

        company = self.env["res.company"].browse(data["company_id"])
        salary_rule = self.env["hr.salary.rule"].browse(data["salary_rule_id"])

        payroll_year = data["payroll_year"]
        month_from = int(data["payroll_month_from"])
        month_to = int(data["payroll_month_to"])

        months = list(range(month_from, month_to + 1))

        headers = [
            "Compañía",
            "Referencia de nómina",
            "Empleado",
            "DNI",
            "Regla salarial",
        ]

        for month in months:
            headers.append("%s-%s" % (
                self.MONTH_NAMES.get(month, ""),
                payroll_year
            ))

        start_row = 0

        for col, header in enumerate(headers):
            sheet.write(start_row, col, header, header_format)


        ##datos
        domain = [
            ("company_id", "=", company.id),
            ("payroll_type", "=", "nomina"),
            ("payroll_year", "=", payroll_year),
            ("payroll_month_number", ">=", month_from),
            ("payroll_month_number", "<=", month_to),
            ("state", "!=", "cancel"),
        ]

        if data["employee_selection"] == "specific":
            domain.append(("employee_id", "in", data["employee_ids"]))

        payslips = self.env["hr.payslip"].search(
            domain,
            order="employee_id, payroll_month_number"
        )

        report_map = {}

        for slip in payslips:
            employee = slip.employee_id
            month = slip.payroll_month_number

            if not employee or not month:
                continue

            employee_key = employee.id

            if employee_key not in report_map:
                report_map[employee_key] = {
                    "employee": employee,
                    "references": {},
                    "amounts": {m: 0.0 for m in months},
                }

            lines = slip.line_ids.filtered(
                lambda line: line.salary_rule_id.id == salary_rule.id
            )

            amount = sum(lines.mapped("total"))

            report_map[employee_key]["amounts"][month] = amount
            report_map[employee_key]["references"][month] = self._get_slip_reference(slip)

        row = start_row + 1
        totals_by_month = {m: 0.0 for m in months}

        for employee_id, values in report_map.items():
            employee = values["employee"]
            amounts = values["amounts"]
            references_by_month = values["references"]

            has_amount = any(amounts.get(month, 0.0) for month in months)

            if not has_amount and not data.get("include_zero"):
                continue

            references = []

            for month in months:
                ref = references_by_month.get(month)
                if ref:
                    references.append("%s: %s" % (
                        self.MONTH_NAMES.get(month, ""),
                        ref
                    ))

            sheet.write(row, 0, company.name or "", text_format)
            sheet.write(row, 1, " | ".join(references), text_format)
            sheet.write(row, 2, employee.name or "", text_format)
            sheet.write(row, 3, employee.identification_id or "", text_format)
            sheet.write(row, 4, salary_rule.name or "", text_format)

            col = 5

            for month in months:
                amount = amounts.get(month, 0.0)
                sheet.write(row, col, amount, money_format)
                totals_by_month[month] += amount
                col += 1

            row += 1

        sheet.write(row, 4, "TOTAL", header_format)

        col = 5

        for month in months:
            sheet.write(row, col, totals_by_month[month], total_format)
            col += 1

        sheet.set_column(0, 0, 40)  # Compañía
        sheet.set_column(1, 1, 30)  # Referencia nómina
        sheet.set_column(2, 2, 35)  # Empleado
        sheet.set_column(3, 3, 15)  # DNI
        sheet.set_column(4, 4, 30)  # Regla salarial

        for col in range(5, 5 + len(months)):
            sheet.set_column(col, col, 16)