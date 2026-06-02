from odoo import models


class ReportZAttendanceCalendarXlsx(models.AbstractModel):
    _name = "report.zattendance.report_calendar_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Reporte General de Horarios XLSX"

    def _float_to_hour_text(self, value):
        hours = int(value or 0.0)
        minutes = int(round(((value or 0.0) - hours) * 60))

        if minutes == 60:
            hours += 1
            minutes = 0

        return "%02d:%02d" % (hours, minutes)

    def generate_xlsx_report(self, workbook, data, wizard):
        employee_selection = data.get("employee_selection")
        employee_ids = data.get("employee_ids") or []
        company_id = data.get("company_id")

        domain = [
            ("employee_id", "!=", False),
        ]

        if company_id:
            domain.append(("employee_id.company_id", "=", company_id))

        if employee_selection == "specific" and employee_ids:
            domain.append(("employee_id", "in", employee_ids))

        calendars = self.env["resource.calendar"].search(
            domain,
            order="employee_id, name",
        )

        sheet = workbook.add_worksheet("Horarios")

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

        number_format = workbook.add_format({
            "border": 1,
            "num_format": "0.00",
            "valign": "vcenter",
        })

        date_format = workbook.add_format({
            "border": 1,
            "num_format": "dd/mm/yyyy",
            "valign": "vcenter",
        })

        headers = [
            "Día",
            "Empleado",
            "Semana",
            "Nro. Identificación",
            "Hora entrada",
            "Hora salida",
            "Tipo de asistencia",
            "Horas presenciales",
            "Horas virtuales",
            "Horas totales",
            "Calendario",
            "Vigencia desde",
            "Vigencia hasta",
        ]

        row = 0

        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)

        row += 1

        day_labels = dict(
            self.env["resource.calendar.attendance"]._fields["dayofweek"].selection
        )

        week_type_labels = dict(
            self.env["resource.calendar.attendance"]._fields["week_type"].selection
        )

        attendance_type_labels = dict(
            self.env["resource.calendar.attendance"]._fields["attendance_type"].selection
        )

        for calendar in calendars:
            employee = calendar.employee_id

            lines = calendar.attendance_ids.sorted(
                key=lambda line: (
                    line.dayofweek or "",
                    line.week_type or "",
                    line.hour_from or 0.0,
                    line.hour_to or 0.0,
                )
            )

            for line in lines:
                planned_presential = line.planned_presential or 0.0
                planned_virtual = line.planned_virtual or 0.0
                planned_total = planned_presential + planned_virtual

                sheet.write(row, 0, day_labels.get(line.dayofweek, ""), text_format)
                sheet.write(row, 1, employee.name or "", text_format)
                sheet.write(row, 2, week_type_labels.get(line.week_type, ""), text_format)
                sheet.write(row, 3, employee.identification_id or "", text_format)
                sheet.write(row, 4, self._float_to_hour_text(line.hour_from), text_format)
                sheet.write(row, 5, self._float_to_hour_text(line.hour_to), text_format)
                sheet.write(
                    row,
                    6,
                    attendance_type_labels.get(line.attendance_type, ""),
                    text_format,
                )
                sheet.write(row, 7, planned_presential, number_format)
                sheet.write(row, 8, planned_virtual, number_format)
                sheet.write(row, 9, planned_total, number_format)
                sheet.write(row, 10, calendar.name or "", text_format)
                sheet.write(row, 11, line.date_from or "", date_format)
                sheet.write(row, 12, line.date_to or "", date_format)

                row += 1

        sheet.set_row(0, 30)

        sheet.set_column(0, 0, 14)   # Día
        sheet.set_column(1, 1, 28)   # Empleado
        sheet.set_column(2, 2, 16)   # Semana
        sheet.set_column(3, 3, 18)   # Nro. Identificación
        sheet.set_column(4, 5, 14)   # Hora entrada/salida
        sheet.set_column(6, 6, 24)   # Tipo asistencia
        sheet.set_column(7, 9, 18)   # Horas
        sheet.set_column(10, 10, 28) # Calendario
        sheet.set_column(11, 12, 16) # Vigencia

        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, row - 1, len(headers) - 1)