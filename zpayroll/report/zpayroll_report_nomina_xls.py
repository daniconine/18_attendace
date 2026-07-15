from odoo import models, fields
from datetime import date


class ReportZPayrollMonthlyXlsx(models.AbstractModel):
    _name = "report.zpayroll.report_payroll_monthly_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Reporte Mensual de Planilla XLSX"

    
    
    
    HEADERS = [
        "Periodo",
        "Mes de pago",
        "Ficha",
        "Apellidos y nombres",
        "Sexo",
        "Fecha de nacimiento",
        "Domicilio",
        "Nacionalidad",
        "DNI",
        "Fecha de ingreso",
        "Cargo u ocupación",
        "Autogenerado EsSalud",
        "CUSPP",
        "AFP",
        "Tipo de comisión AFP",
        "Tipo de contrato",
        "Tipo de personal",
        "Sueldo mensual contractual",
        "Días laborados",
        "Horas laboradas del mes",
        "Días vacaciones",
        "Fecha inicio vacaciones",
        "Fecha fin vacaciones",
        "Sueldo básico",
        "Asignación familiar",
        "Feriado 1 de mayo",
        "Horas extras",
        "Clases dictadas",
        "Comisión por ventas",
        "Compensación vacacional",
        "Bonificación",
        "Vacaciones",
        "Vacaciones truncas",
        "Vacaciones pendientes",
        "Gratificación",
        "Gratificación trunca",
        "Bonificación extraordinaria Ley 29351/30334",
        "Utilidad",
        "Otros ingresos",
        "Total ingresos",
        "Tardanza",
        "Falta injustificada",
        "Total ingresos afectos",
        "ONP / SNP 13%",
        "AFP fondo",
        "AFP comisión porcentual",
        "AFP seguro",
        "Total AFP",
        "Renta de quinta categoría",
        "EPS trabajador",
        "Adelanto",
        "Descuento por gratificación",
        "Descuento por utilidad",
        "Préstamo de terceros",
        "Otros descuentos",
        "Total descuentos",
        "Neto a pagar",
        "Aporte EPS empleador",
        "EsSalud",
        "Total aportes empleador",
    ]

    RULE_MAP = {
        # Ingresos
        "sueldo_basico": ["BASIC"],
        "asignacion_familiar": ["ASIG_FAMILIAR"],
        "vacaciones": ["VAC"],
        "horas_extras": ["hrs_25", "hrs_35", "hrs_100", "hrs_200"],
        "clases": ["CLASES"],
        "comision_ventas": ["COMISION"],
        "bonificacion": ["BONO"],

        # Gratificación y bonificación extraordinaria
        "gratificacion": ["GRATI_JULIO", "GRATI_DICIEMBRE"],
        "bonificacion_extraordinaria": ["BONIF_JULIO", "BONIF_DICIEMBRE"],

        # Totales
        "total_ingresos": ["GROSS"],

        # Descuentos
        "tardanza": ["TARDE"],
        "falta_injustificada": ["FALTAS"],
        "onp": ["ONP"],
        "afp_fondo": ["AFP-FONDO"],
        "afp_comision": ["AFP-COMISION"],
        "afp_seguro": ["AFP-SEGURO"],
        "renta_5ta": ["R5_RET"],

        # Nuevos descuentos
        "eps_trabajador": ["DESC_EPS"],
        "prestamo_terceros": ["PRESTAMO_TRAB"],
        "descuento_gratificacion": ["DESC_GRATI_PAGADA"],

        # Otros descuentos
        "otros_descuentos": ["Desc_OTROS"],

        # Neto
        "neto_pagar": ["NET"],

        # Aportes empleador
        "essalud": ["APORTE_ESSALUD"],
        "eps_empleador": ["APORTE_EPS"],

        # Por ahora sin regla definida
        "feriado_1_mayo": [],
        "compensacion_vacacional": [],
        "vacaciones_truncas": [],
        "vacaciones_pendientes": [],
        "gratificacion_trunca": [],
        "utilidad": [],
        "otros_ingresos": [],
        "total_ingresos_afectos": [],
        "adelanto": [],
        "descuento_utilidad": [],
    }
    
    def generate_xlsx_report(self, workbook, data, wizard):
        sheet = workbook.add_worksheet("Planilla")
                
        header_format = workbook.add_format({
            "bold": True,
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        })

        money_format = workbook.add_format({
            "num_format": "#,##0.00",
            "border": 1,
        })

        text_format = workbook.add_format({
            "border": 1,
        })

        date_format = workbook.add_format({
                "num_format": "dd/mm/yyyy",
                "border": 1,
            })
        
        payroll_month = data.get("payroll_month")
        payroll_year = str(data.get("payroll_year") or "").strip()
        company_id = data.get("company_id")
        employee_selection = data.get("employee_selection")
        employee_ids = data.get("employee_ids") or []

        domain = [
            ("payroll_type", "=", "nomina"),
            ("payroll_month", "=", payroll_month),
            ("payroll_year", "=", payroll_year),
        ]

        if company_id:
            domain.append(("company_id", "=", company_id))

        if employee_selection == "specific" and employee_ids:
            domain.append(("employee_id", "in", employee_ids))

        payslips = self.env["hr.payslip"].search(
            domain,
            order="employee_id, date_from"
        )

        for col, header in enumerate(self.HEADERS):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 18)

        row = 1

        for slip in payslips:
            employee = slip.employee_id
            contract = slip.contract_id

            line_amounts = self._get_line_amounts(slip)

            # Ingresos
            sueldo_basico = self._get_rule_amount(line_amounts, "sueldo_basico")
            asignacion_familiar = self._get_rule_amount(line_amounts, "asignacion_familiar")
            feriado_1_mayo = self._get_rule_amount(line_amounts, "feriado_1_mayo")
            horas_extras = self._get_rule_amount(line_amounts, "horas_extras")
            clases = self._get_rule_amount(line_amounts, "clases")
            comision_ventas = self._get_rule_amount(line_amounts, "comision_ventas")
            compensacion_vacacional = self._get_rule_amount(line_amounts, "compensacion_vacacional")
            bonificacion = self._get_rule_amount(line_amounts, "bonificacion")
            vacaciones = self._get_rule_amount(line_amounts, "vacaciones")
            vacaciones_truncas = self._get_rule_amount(line_amounts, "vacaciones_truncas")
            vacaciones_pendientes = self._get_rule_amount(line_amounts, "vacaciones_pendientes")
            gratificacion = self._get_rule_amount(line_amounts, "gratificacion")
            gratificacion_trunca = self._get_rule_amount(line_amounts, "gratificacion_trunca")
            bonificacion_extraordinaria = self._get_rule_amount(line_amounts, "bonificacion_extraordinaria")
            utilidad = self._get_rule_amount(line_amounts, "utilidad")
            otros_ingresos = self._get_rule_amount(line_amounts, "otros_ingresos")
            total_ingresos = self._get_rule_amount(line_amounts, "total_ingresos")

            # Descuentos
            tardanza = self._get_rule_amount_abs(line_amounts, "tardanza")
            falta_injustificada = self._get_rule_amount_abs(line_amounts, "falta_injustificada")
            onp = self._get_rule_amount_abs(line_amounts, "onp")
            afp_fondo = self._get_rule_amount_abs(line_amounts, "afp_fondo")
            afp_comision = self._get_rule_amount_abs(line_amounts, "afp_comision")
            afp_seguro = self._get_rule_amount_abs(line_amounts, "afp_seguro")
            total_afp = afp_fondo + afp_comision + afp_seguro
            renta_5ta = self._get_rule_amount_abs(line_amounts, "renta_5ta")
            eps_trabajador = self._get_rule_amount_abs(line_amounts, "eps_trabajador")
            adelanto = self._get_rule_amount_abs(line_amounts, "adelanto")
            descuento_gratificacion = self._get_rule_amount_abs(line_amounts, "descuento_gratificacion")
            descuento_utilidad = self._get_rule_amount_abs(line_amounts, "descuento_utilidad")
            prestamo_terceros = self._get_rule_amount_abs(line_amounts, "prestamo_terceros")
            otros_descuentos = self._get_rule_amount_abs(line_amounts, "otros_descuentos")

            total_descuentos = (
                tardanza
                + falta_injustificada
                + onp
                + total_afp
                + renta_5ta
                + eps_trabajador
                + adelanto
                + descuento_gratificacion
                + descuento_utilidad
                + prestamo_terceros
                + otros_descuentos
            )

            # Neto y aportes
            neto_pagar = self._get_rule_amount(line_amounts, "neto_pagar")
            eps_empleador = self._get_rule_amount(line_amounts, "eps_empleador")
            essalud = self._get_rule_amount(line_amounts, "essalud")
            total_aportes_empleador = eps_empleador + essalud

            total_ingresos_afectos = self._get_rule_amount(line_amounts, "total_ingresos_afectos")

            values = [
                self._get_period_label(slip),
                slip.date_to,
                employee.barcode or "",
                employee.name or "",
                employee.gender or "",
                employee.birthday or "",
                employee.private_street or "",
                employee.country_id.name or "",
                employee.identification_id or "",
                employee.first_contract_date or "",
                employee.job_id.name or "",
                getattr(employee, "essalud_code", "") or "",
                getattr(employee, "cuspp", "") or "",
                getattr(employee, "afp_id", False).name if getattr(employee, "afp_id", False) else "",
                getattr(employee, "afp_commission_type", "") or "",
                contract.contract_type_id.name if contract and contract.contract_type_id else "",
                getattr(employee, "employee_type", "") or "",
                contract.wage if contract else 0.0,
                self._get_worked_days(slip),
                self._get_worked_hours(slip),
                0.0,
                "",
                "",
                sueldo_basico,
                asignacion_familiar,
                feriado_1_mayo,
                horas_extras,
                clases,
                comision_ventas,
                compensacion_vacacional,
                bonificacion,
                vacaciones,
                vacaciones_truncas,
                vacaciones_pendientes,
                gratificacion,
                gratificacion_trunca,
                bonificacion_extraordinaria,
                utilidad,
                otros_ingresos,
                total_ingresos,
                tardanza,
                falta_injustificada,
                total_ingresos_afectos,
                onp,
                afp_fondo,
                afp_comision,
                afp_seguro,
                total_afp,
                renta_5ta,
                eps_trabajador,
                adelanto,
                descuento_gratificacion,
                descuento_utilidad,
                prestamo_terceros,
                otros_descuentos,
                total_descuentos,
                neto_pagar,
                eps_empleador,
                essalud,
                total_aportes_empleador,
            ]

            for col, value in enumerate(values):
                if isinstance(value, date):
                    sheet.write_datetime(row, col, value, date_format)
                elif isinstance(value, (int, float)):
                    sheet.write(row, col, value, money_format)
                else:
                    sheet.write(row, col, value or "", text_format)

            row += 1

    def _get_line_amounts(self, slip):
        result = {}
        for line in slip.line_ids:
            code = line.code
            result[code] = result.get(code, 0.0) + line.total
        return result
    
    def _get_rule_amount(self, line_amounts, key):
        codes = self.RULE_MAP.get(key, [])
        return sum(line_amounts.get(code, 0.0) for code in codes)


    def _get_rule_amount_abs(self, line_amounts, key):
        return abs(self._get_rule_amount(line_amounts, key))

    def _get_amount(self, line_amounts, codes):
        return sum(line_amounts.get(code, 0.0) for code in codes)

    def _get_period_label(self, slip):
        if slip.date_from and slip.date_to:
            return "%s - %s" % (slip.date_from.strftime("%d/%m/%Y"), slip.date_to.strftime("%d/%m/%Y"))
        return ""

    def _get_worked_days(self, slip):
        return sum(slip.worked_days_line_ids.mapped("number_of_days"))

    def _get_worked_hours(self, slip):
        return sum(slip.worked_days_line_ids.mapped("number_of_hours"))