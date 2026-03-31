from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import xlrd
from datetime import datetime, timedelta
import calendar
import logging

_logger = logging.getLogger(__name__)

class HrAttendanceImport(models.Model):
    _name = 'hr.attendance.import'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Importador de Asistencias desde Excel'
    _order = 'year desc, month desc'

    name = fields.Char(string="Referencia", compute='_compute_name', store=True)
    year = fields.Selection(
        [(str(y), str(y)) for y in range(datetime.now().year - 2, datetime.now().year + 7)],
        string="Año", required=True, default=lambda self: str(datetime.now().year)
    )
    month = fields.Selection([
        ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'), ('4', 'Abril'),
        ('5', 'Mayo'), ('6', 'Junio'), ('7', 'Julio'), ('8', 'Agosto'),
        ('9', 'Septiembre'), ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
    ], string="Mes", required=True, default=lambda self: str(datetime.now().month))
    location_id = fields.Many2one('hr.attendance.location', string="Sede")
    
    file_data = fields.Binary(string="Archivo Excel (.xlsx)", required=True)
    file_name_placeholder = fields.Char(string="Nombre del Archivo", default="asistencias.xlsx")
    sheet_name = fields.Char(string="Nombre de la Pestaña")
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('read', 'Archivo Leído'),
        ('validated', 'Líneas Validadas'),
        ('done', 'Asistencias Creadas'),
        ('error', 'Error de Validación')
    ], string="Estado", default='draft', readonly=True, copy=False, tracking=True)

    line_ids = fields.One2many('hr.attendance.import.line', 'import_id', string="Registros de Asistencia Validados")
    log = fields.Text(string="Registro de Eventos", readonly=True)

    @api.depends('location_id', 'year', 'month')
    def _compute_name(self):
        for record in self:
            parts = ["Importación Asistencia"]
            
            if record.location_id:
                parts.append(record.location_id.name)
            
            # Añadimos el mes y el año para mayor claridad
            if record.month and record.year:
                month_name = dict(record._fields['month'].selection).get(record.month)
                parts.append(f"{month_name} {record.year}")
            
            record.name = " - ".join(parts)

     # --- ACCIÓN 1: LEER ---
    def action_read_file(self):
        self.ensure_one()
        if not self.file_data: raise UserError(_("Por favor, suba un archivo de Excel."))
        
        self.line_ids.unlink()
        self.log = ""
        
        try:
            workbook = xlrd.open_workbook(file_contents=base64.b64decode(self.file_data), on_demand=True)
            sheet = workbook.sheet_by_name(self.sheet_name) if self.sheet_name else workbook.sheet_by_index(0)
        except Exception as e:
            self.state = 'error'; self.log = f"Error crítico al leer el archivo Excel: {e}"; return

        try:
            year = int(self.year)
            month = int(self.month)
            days_in_month = calendar.monthrange(year, month)[1]
        except Exception as e:
            self.state = 'error'; self.log = f"Año o mes inválido seleccionado. Error: {e}"; return

        
        lines_vals = []
        
        # Iterar por bloques de empleados, empezando en la fila 5 (índice 4) y saltando de 2 en 2
        current_row_idx = 4
        while current_row_idx < sheet.nrows:
            try:
                # ➤ CORRECCIÓN: Leer ID (Col C, índice 2) y Nombre (Col K, índice 10)
                zk_id_raw = sheet.cell_value(current_row_idx, 2)
                employee_name_raw = sheet.cell_value(current_row_idx, 10)
                
                if not zk_id_raw: break

                zk_id_str = str(int(zk_id_raw)) if isinstance(zk_id_raw, float) else str(zk_id_raw).strip()

                # Iterar por las columnas de los días
                for day in range(1, days_in_month + 1):
                    # ➤ CORRECCIÓN: El día 1 está en la Columna A (índice 0)
                    col_idx = day - 1 

                    # Leer la celda de marcaciones (fila del ID + 1)
                    try:
                        cell_value = sheet.cell_value(current_row_idx + 1, col_idx)
                    except IndexError:
                        # Si hay un error de índice aquí, significa que se acabaron las columnas para este mes.
                        # Rompemos el bucle de los días, pero NO el de los empleados.
                        break

                    if not cell_value: continue

                    # 1. Convertimos el contenido de la celda a una cadena limpia, sin espacios.
                    #    Ej: '09:0413:0214:5820:05'
                    time_string = str(cell_value).replace(":", "").replace(" ", "").strip()
                    
                    # 2. Partimos la cadena en trozos de 4 caracteres ('HHMM')
                    #    Ej: ['0904', '1302', '1458', '2005']
                    times_unformatted = [time_string[i:i+4] for i in range(0, len(time_string), 4)]

                    # 3. Reinsertamos los ':' para tener un formato estándar 'HH:MM'
                    #    Ej: ['09:04', '13:02', '14:58', '20:05']
                    clean_times = [f"{t[:2]}:{t[2:]}" for t in times_unformatted if len(t) == 4]
                    
                    if not clean_times: continue
                    
                    # Formar parejas de check-in/check-out
                    for i in range(0, len(clean_times), 2):
                        check_in_str = clean_times[i]
                        check_out_str = clean_times[i+1] if i + 1 < len(clean_times) else ''
                        
                        lines_vals.append({
                            'import_id': self.id, 'row_index': current_row_idx + 1,
                            'day_str': str(day), 'zkteco_id_raw': zk_id_str,
                            'employee_name_raw': employee_name_raw,
                            'check_in_str_raw': check_in_str, 'check_out_str_raw': check_out_str,
                        })
                        
            except IndexError: break
            
            # Saltar 2 filas al siguiente bloque de empleado
            current_row_idx += 2

        if lines_vals:
            self.env['hr.attendance.import.line'].create(lines_vals)

        self.write({
            'state': 'read',
            'log': f'Archivo leído. Se encontraron {len(lines_vals)} registros de entrada/salida para validar.'
        })
        
        workbook.release_resources()
        del workbook

    # --- ACCIÓN 2: VALIDAR ---
    def action_validate_lines(self):
        self.ensure_one()
        location_id = self.location_id
        if self.state not in ['read', 'error']: raise UserError(_("Solo se pueden validar importaciones en estado 'Archivo Leído' o 'Error'."))

        employee_map = {m.zkteco_id: m.employee_id for m in self.env['hr.employee.zkteco'].search([('location_id','=',location_id.id)])}
        errors = []

        for line in self.line_ids.filtered(lambda l: l.state == 'draft'):
            vals_to_write = {}
            line_errors = []

            # Validar empleado
            employee = employee_map.get(line.zkteco_id_raw)
            if not employee:
                employee = self.sudo().env['hr.employee'].sudo().search([('name','ilike',line.employee_name_raw.strip())], limit=1)
                if line.zkteco_id_raw and employee:
                    employee_zkteco_id = self.env['hr.employee.zkteco'].create({
                        'location_id': location_id.id,
                        'employee_id': employee.id,
                        'zkteco_id': line.zkteco_id_raw,
                    })
                    employee_map[line.zkteco_id_raw] = employee
            if not employee: line_errors.append("ID de marcador no mapeado.")
            else: vals_to_write['employee_id'] = employee.id
            
            # Validar y construir Datetimes usando year, month y day_str
            try:
                # ➤ CORRECCIÓN: Usamos los campos del importador, no volvemos a leer el archivo
                date_str = f"{self.year}-{self.month}-{line.day_str}"
                check_in = datetime.strptime(f"{date_str} {line.check_in_str_raw}", '%Y-%m-%d %H:%M')
                check_in += timedelta(hours=5)
                vals_to_write['check_in'] = check_in
                if line.check_out_str_raw:
                    check_out = datetime.strptime(f"{date_str} {line.check_out_str_raw}", '%Y-%m-%d %H:%M')
                    check_out += timedelta(hours=5)
                    vals_to_write['check_out'] = check_out
            except Exception as e:
                line_errors.append(f"Formato de fecha/hora inválido. Error: {e}")

            if line_errors:
                vals_to_write['state'] = 'error'
                vals_to_write['error_message'] = "\n".join(line_errors)
                errors.extend([f"Fila {line.row_index}, Día {line.day_str}: {e}" for e in line_errors])
            else:
                vals_to_write['state'] = 'valid'
                vals_to_write['error_message'] = '' # Limpiamos errores previos
            
            line.write(vals_to_write)
        
        if errors:
            self.write({'state': 'error', 'log': "Validación completada con errores:\n" + "\n".join(errors)})
        else:
            self.write({'state': 'validated', 'log': "Todas las líneas han sido validadas correctamente."})


    # --- ACCIÓN 3: CREAR ASISTENCIAS ---
    def action_create_attendances(self):
        self.ensure_one()
        if self.state != 'validated': raise UserError(_("Solo se pueden crear asistencias si todas las líneas han sido validadas."))
        
        valid_lines = self.line_ids.filtered(lambda l: l.state == 'valid')
        attendances_to_create = []
        for line in valid_lines:
            if not self.env['hr.attendance'].search_count([('employee_id', '=', line.employee_id.id), ('check_in', '=', line.check_in)]):
                check_out = line.check_out or (line.check_in + timedelta(minutes=1))
                attendances_to_create.append({'employee_id': line.employee_id.id, 'check_in': line.check_in, 'check_out': check_out})
        
        if attendances_to_create:
            attendances = self.env['hr.attendance'].with_context(attendance_import=True).create(attendances_to_create)
            # crea inasistencias
            unpaid_leave_type = self.env.ref(
                'mstech_payroll_extend.leave_type_unpaid_pe', 
                raise_if_not_found=False
            )
            date_start = fields.Date.context_today(self).replace(year=int(self.year), month=int(self.month), day=1)
            date_end = fields.Date.add(date_start, months=1)
            employees = attendances.employee_id
            employees = employees.filtered(lambda e: e.contract_id and e.contract_id.state == 'open' and not e.contract_id.is_trusted_employee)
            employees.create_unjustified_absences(date_start, date_end, unpaid_leave_type)

        valid_lines.write({'state': 'done'})
        self.write({'state': 'done', 'log': self.log + f"\n\nProceso finalizado. Se crearon {len(attendances_to_create)} asistencias."})

    # --- ACCIÓN 4: REPROCESAR ---
    def action_reset_to_draft(self):
        self.line_ids.unlink()
        self.write({'state': 'draft', 'log': ''})


class HrAttendanceImportLine(models.Model):
    _name = 'hr.attendance.import.line'
    _description = 'Línea de Asistencia para Importación'
    _order = 'row_index, check_in'

    import_id = fields.Many2one('hr.attendance.import', ondelete='cascade')
    row_index = fields.Integer(string="Fila #", readonly=True)

    # --- DATOS CRUDOS DEL EXCEL (PARA TRAZABILIDAD) ---
    zkteco_id_raw = fields.Char(string="ID Marcador (Excel)", readonly=True)
    employee_name_raw = fields.Char(string="Nombre (Excel)", readonly=True)
    check_in_str_raw = fields.Char(string="Entrada (Excel)", readonly=True)
    check_out_str_raw = fields.Char(string="Salida (Excel)", readonly=True)
    day_str = fields.Char(string="Día (Excel)", readonly=True)

    # --- DATOS PROCESADOS Y VALIDADOS ---
    employee_id = fields.Many2one('hr.employee', string="Empleado Odoo", readonly=True)
    check_in = fields.Datetime(string="Entrada Validada", readonly=False)
    check_out = fields.Datetime(string="Salida Validada", readonly=False)
    
    state = fields.Selection([
        ('draft', 'Pendiente de Validación'),
        ('valid', 'Válido'),
        ('error', 'Error'),
        ('done', 'Creado en Asistencias')
    ], string="Estado", default='draft', readonly=True)
    error_message = fields.Text(string="Mensaje de Error", readonly=True)

    conflicting_register = fields.Boolean(string="Conflicto", compute="_compute_conflicting_register")

    def _compute_conflicting_register(self):
        for record in self:
            to_write = {'conflicting_register': False}
            if record.import_id and record.employee_id and record.check_in and record.state=='valid':
                real_count = self.env['hr.attendance.import.line'].search_count([
                    ('import_id', '=', record.import_id.id),
                    ('employee_id', '=', record.employee_id.id),
                    ('day_str', '=', record.day_str),
                ])
                schedule_count = len(record.employee_id.resource_calendar_id.attendance_ids.filtered(lambda x: x.dayofweek == str(record.check_in.weekday())))
                if schedule_count < real_count:
                    to_write['conflicting_register'] = True
            record.write(to_write)


class HrAttendanceLocation(models.Model):
    _name = 'hr.attendance.location'
    _description = 'Sede o Ubicación de Marcador de Asistencia'

    name = fields.Char(string="Nombre de la Sede", required=True)
    employee_mapping_ids = fields.One2many(
        'hr.employee.zkteco',
        'location_id',
        string="Mapeo de Empleados"
    )

class HrEmployeeZkteco(models.Model):
    _name = 'hr.employee.zkteco'
    _description = 'Mapeo de ID Externo de Asistencia a Empleado'
    _rec_name = 'employee_id'

    location_id = fields.Many2one('hr.attendance.location', string="Sede")
    
    zkteco_id = fields.Char(string="ID en Marcador (ZKTeco)", required=True)
    employee_id = fields.Many2one('hr.employee', string="Empleado en Odoo", required=True)

    _sql_constraints = [
        ('zkteco_id_uniq', 'unique(zkteco_id, location_id)', 'El ID del marcador debe ser único por Sede.')
    ]