# mstech_payroll_extend/models/report_template.py

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

import base64
import logging

_logger = logging.getLogger(__name__)


class HrReportTemplate(models.Model):
    _name = 'hr.report.template'
    _description = 'Plantilla para Generador de Reportes de Nómina'

    name = fields.Char(string="Nombre de la Plantilla", required=True)
    file_extension = fields.Char(string="Extensión del Archivo", required=True, default="txt")
    delimiter = fields.Char(string="Separador de Columnas", default="|")
    filename = fields.Char(string="Nombre de archivo", help="Opcional. Utilice una expresión de python (disponible 'payslip_run')")
    iterator = fields.Char(string="Lineas internas", help="Opcional. Defina el campo de payslip a tomar como referencia.")

    line_ids = fields.One2many('hr.report.template.line', 'template_id', string="Definición de Columnas")
    is_bank_payment = fields.Boolean(string="Es para Pago Bancario", help="Marca esta casilla si la plantilla es para un archivo de pago masivo.")

    # --- MÉTODO CENTRAL DE GENERACIÓN ---
    def _generate_report_from_template(self, template, payslips, payslip_run):
        """
        Genera un archivo de reporte basado en esta plantilla y un conjunto de nóminas.
        :param template: self, la plantilla a usar
        :param payslips: recordset de hr.payslip
        :param payslip_run: el lote de nóminas de origen
        """
        file_content_rows = []
        for slip in payslips:
            _logger.info('Payslip: ' + str(slip.name))
            iterator = slip.mapped(template.iterator) if template.iterator else [False]
            for item in iterator:
                row_columns = []
                for col in template.line_ids:
                    value = self._get_column_value(col, slip, add_context={'item': item})
                    formatted_value = self._format_value(value, col)
                    row_columns.append(formatted_value)
                _logger.info('"'+ str(row_columns) + '"')
                if any(row_columns):
                    file_content_rows.append(template.delimiter.join(row_columns))
        
        _logger.info('rows:')
        _logger.info('"'+ str(file_content_rows) + '"')
        final_file_content = "\n".join(file_content_rows)

        # Guardar el archivo en un registro hr.report.file
        file_name = ''
        if template.filename:
            context = {
                'payslip_run': payslip_run,
            }
            file_name = f"{str(safe_eval(template.filename, context))}"
        else:
            file_name = f"{payslip_run.name.replace(' ', '_')}_{template.name.replace(' ', '_')}"
        
        file_name += '.' + str(template.file_extension)
        
        file_data = base64.b64encode(final_file_content.encode('utf-8'))
        self.env['hr.report.file'].create({
            'name': template.name,
            'payslip_run_id': payslip_run.id,
            'file_data': file_data or file_data.decode(),
            'file_name': file_name,
        })
        return True

    def _get_column_value(self, col, payslip, add_context={}):
        """Obtiene el valor de una columna según su tipo."""
        if col.value_type == 'fixed':
            return col.fixed_value or ''
            
        context = {
            'payslip': payslip,
            'employee': payslip.employee_id,
            'contract': payslip.contract_id,
            'bank': payslip.contract_id.bank_id,
        }
        context.update(add_context)
        
        if col.value_type == 'field':
            try:
                # safe_eval puede navegar por los campos relacionados
                return str(safe_eval(f"payslip.{col.field_path}", context))
            except Exception:
                return ''
        
        if col.value_type == 'python':
            script = col.code_executor_id
            if script:
                script.with_context(context=context).action_execute_code()
                result_str = script.code_result or ''
                return result_str.rstrip()
            try:
                return str(safe_eval(col.python_code, context))
            except Exception:
                return ''
        return ''

    def _format_value(self, value, col):
        """Aplica el formato de padding y longitud."""
        if not col.padding_length:
            return value
        
        value = value[:col.padding_length] # Truncar si es más largo
        
        if col.padding_align == 'right':
            return value.rjust(col.padding_length, col.padding_char)
        elif col.padding_align == 'left':
            return value.ljust(col.padding_length, col.padding_char)
        else:
            return value


class HrReportTemplateLine(models.Model):
    _name = 'hr.report.template.line'
    _description = 'Línea/Columna de Plantilla de Reporte'
    _order = 'sequence'

    template_id = fields.Many2one('hr.report.template', ondelete='cascade')
    sequence = fields.Integer(default=10)
    
    name = fields.Char(string="Nombre de Columna", required=True)
    
    value_type = fields.Selection([
        ('fixed', 'Valor Fijo'),
        ('field', 'Campo de Odoo'),
        ('python', 'Código Python'),
    ], string="Tipo de Valor", required=True)

    # Valor a usar según el tipo
    fixed_value = fields.Char(string="Valor Fijo")
    field_path = fields.Char(string="Ruta del Campo", help="Ej: employee_id.name, contract_id.bank_account_number, line_ids.filtered(lambda l: l.code == 'NET_PE').total")
    python_code = fields.Text(string="Código Python", help="Variables disponibles: payslip, employee, contract, bank. Debe retornar un string.")
    
    # Formato
    padding_char = fields.Char(string="Carácter de Relleno", size=1, default=' ')
    padding_length = fields.Integer(string="Longitud Fija")
    padding_align = fields.Selection([('left', 'Izquierda (Relleno a la derecha)'), ('right', 'Derecha (Relleno a la izquierda)')], string="Alineación")
    code_executor_id = fields.Many2one(string="Code Executor", comodel_name="python.code.execute")
