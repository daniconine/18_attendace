import base64
from io import BytesIO
import xlsxwriter
from odoo import models, fields

class ExcelReport(models.TransientModel):
    _name = 'excel.report'
    _description = 'Generar Reporte Excel'

    def generate_excel_report(self):
        # Crear un objeto Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Datos de ejemplo
        data = [
            ['ID', 'Nombre', 'Edad'],
            [1, 'Juan Pérez', 30],
            [2, 'Ana López', 25],
            [3, 'Carlos Gómez', 35],
        ]

        # Escribir los datos en el archivo Excel
        for row_num, row_data in enumerate(data):
            worksheet.write_row(row_num, 0, row_data)

        # Guardar el archivo
        workbook.close()

        # Volver al inicio del archivo para leerlo
        output.seek(0)
        
        # Codificar los datos en base64
        file_data = base64.b64encode(output.read()).decode('utf-8')  # Esto es lo correcto en Python 3
        
        # Crear un archivo adjunto en Odoo
        attachment = self.env['ir.attachment'].create({
            'name': 'reporte.xlsx',
            'type': 'binary',
            'datas': file_data,  # Se debe usar 'datas' con el archivo codificado en base64
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return attachment
