from odoo import fields, models


#reportte personalziado de asistencia
class ReportZAttendanceXlsx(models.AbstractModel):
    _name = "report.zattendance.report_zattendance_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Reporte SUNAFIL XLSX"

    def generate_xlsx_report(self, workbook, data, wizard):
        date_from = fields.Date.from_string(data.get("date_from"))
        date_to = fields.Date.from_string(data.get("date_to"))
        employee_selection = data.get("employee_selection")
        employee_ids = data.get("employee_ids") or []
        company_id = data.get("company_id")

        domain = [
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]

        if company_id:
            domain.append(("company_id", "=", company_id))

        if employee_selection == "specific" and employee_ids:
            domain.append(("employee_id", "in", employee_ids))

        records = self.env["zattendance.day"].search(
            domain,
            order="employee_id, date",
        )

        sheet = workbook.add_worksheet("SUNAFIL")

        header_format = workbook.add_format({
            "bold": True,
            "bg_color": "#D9EAF7",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        })

        text_format = workbook.add_format({
            "border": 1,
            "valign": "vcenter",
        })

        date_format = workbook.add_format({
            "border": 1,
            "num_format": "dd/mm/yyyy",
            "valign": "vcenter",
        })

        datetime_format = workbook.add_format({
            "border": 1,
            "num_format": "dd/mm/yyyy hh:mm",
            "valign": "vcenter",
        })

        number_format = workbook.add_format({
            "border": 1,
            "num_format": "0.00",
            "valign": "vcenter",
        })

        integer_format = workbook.add_format({
            "border": 1,
            "num_format": "0",
            "valign": "vcenter",
        })

        headers = [
            "Empleado",
            "Nro. Identificación",
            "Fecha",
            "Día",
            "Tipo asignado",
            "Entrada horario",
            "Salida horario",
            "Horas presenciales planif.",
            "Horas virtuales planif.",
            "Horas totales planif.",
            "Entrada real",
            "Salida real",
            "Horas presenciales reales",
            "Horas virtuales reales",
            "Horas totales reales",
            "Exceso/Defecto",
            "Tipo calculado",
            "Estado",
            "Tardanza min.",
        ]

        row = 0

        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)

        row += 1

        weekday_labels = dict(
            self.env["zattendance.day"]._fields["weekday"].selection
        )

        planned_type_labels = dict(
            self.env["zattendance.day"]._fields["planned_attendance_type"].selection
        )

        tipo_asistencia_labels = dict(
            self.env["zattendance.day"]._fields["tipo_asistencia"].selection
        )

        state_labels = dict(
            self.env["zattendance.day"]._fields["state"].selection
        )

        for rec in records:
            sheet.write(row, 0, rec.employee_id.name or "", text_format)
            sheet.write(row, 1, rec.employee_id.identification_id or "", text_format)
            sheet.write(row, 2, rec.date or "", date_format)
            sheet.write(row, 3, weekday_labels.get(rec.weekday, ""), text_format)

            sheet.write(
                row,
                4,
                planned_type_labels.get(rec.planned_attendance_type, ""),
                text_format,
            )

            sheet.write(row, 5, rec.planned_start or "", datetime_format)
            sheet.write(row, 6, rec.planned_end or "", datetime_format)

            sheet.write(row, 7, rec.planned_presential or 0.0, number_format)
            sheet.write(row, 8, rec.planned_virtual or 0.0, number_format)
            sheet.write(row, 9, rec.planned_total or 0.0, number_format)

            sheet.write(row, 10, rec.actual_first_check_in or "", datetime_format)
            sheet.write(row, 11, rec.actual_last_check_out or "", datetime_format)

            sheet.write(row, 12, rec.actual_presential or 0.0, number_format)
            sheet.write(row, 13, rec.actual_virtual or 0.0, number_format)
            sheet.write(row, 14, rec.actual_total or 0.0, number_format)
            sheet.write(row, 15, rec.diff_attendance or 0.0, number_format)

            sheet.write(
                row,
                16,
                tipo_asistencia_labels.get(rec.tipo_asistencia, ""),
                text_format,
            )

            sheet.write(row, 17, state_labels.get(rec.state, ""), text_format)
            sheet.write(row, 18, rec.late_min or 0, integer_format)

            row += 1

        sheet.set_row(0, 30)

        sheet.set_column(0, 0, 28)   # Empleado
        sheet.set_column(1, 1, 18)   # Nro. Identificación
        sheet.set_column(2, 3, 14)   # Fecha, Día
        sheet.set_column(4, 4, 24)   # Tipo asignado
        sheet.set_column(5, 6, 20)   # Entrada/Salida horario
        sheet.set_column(7, 9, 22)   # Horas planificadas
        sheet.set_column(10, 11, 20) # Entrada/Salida real
        sheet.set_column(12, 15, 22) # Horas reales y diferencia
        sheet.set_column(16, 17, 18) # Tipo calculado, Estado
        sheet.set_column(18, 18, 14) # Tardanza

        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, row - 1, len(headers) - 1)