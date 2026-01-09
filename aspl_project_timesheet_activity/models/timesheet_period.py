from odoo import fields, models

class TimesheetPeriod(models.Model):
    _name = "timesheet.period"
    _description = "Periodo de Timesheet (corte 25→24)"

    name = fields.Char(string="Nombre Periodo Hoja Tiempos", required=True)
    date_start = fields.Date(string="Fecha Inicio del Periodo", required=True)
    date_end = fields.Date(string="Fecha Fin del Periodo", required=True)
    company_id = fields.Many2one("res.company", string="Compañía", default=lambda self: self.env.company)
    state = fields.Selection([
        ("open", "Abierto"),
        ("closed", "Cerrado"),
    ], string="Estado", default="open")

    timesheet_line_ids = fields.One2many(
        "account.analytic.line", "x_period_id", string="Líneas Hojas de Tiempo"
    )
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True)
        

class TimesheetPeriodHExtras(models.Model):
    _name = "timesheet.period.hextras"
    _description = "Periodo de Timesheet Horas Extras (corte 25→24)"

    name = fields.Char(string="Nombre Periodo Horas Extras", required=True)
    date_start = fields.Date(string="Fecha Inicio del Periodo", required=True)
    date_end = fields.Date(string="Fecha Fin del Periodo", required=True)
    company_id = fields.Many2one("res.company", string="Compañía", default=lambda self: self.env.company)
    state = fields.Selection([
        ("open", "Abierto"),
        ("closed", "Cerrado"),
    ], string="Estado", default="open")

    timesheet_line_ids = fields.One2many(
        "account.analytic.line", "x_periodo_hextras_id", string="Líneas de Horas Extras"
    )
    
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True)

    # Campo para indicar si el jefe ha aprobado o rechazado
    approval_state = fields.Selection([
        ('draft', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], string='Aprobación del Jefe', default='draft', tracking=True)
    
    
    
    def approve(self):
        """Método para aprobar el período y las líneas asociadas"""
        self.write({'approval_state': 'approved'})
        # Aprobar automáticamente todas las líneas asociadas
        for line in self.timesheet_line_ids:
            line.write({'state': 'approved'})

    def reject(self):
        """Método para rechazar el período y las líneas asociadas"""
        self.write({'approval_state': 'rejected'})
        # Rechazar automáticamente todas las líneas asociadas
        for line in self.timesheet_line_ids:
            line.write({'state': 'rejected'})

    
class TimesheetPeriodComisiones(models.Model):
    _name = "timesheet.period.comisiones"
    _description = "Periodo de Timesheet Comisiones (corte 25→24)"

    name = fields.Char(string="Nombre Periodo Comisiones", required=True)
    date_start = fields.Date(string="Fecha Inicio del Periodo", required=True)
    date_end = fields.Date(string="Fecha Fin del Periodo", required=True)
    company_id = fields.Many2one("res.company", string="Compañía", default=lambda self: self.env.company)
    state = fields.Selection([
        ("open", "Abierto"),
        ("closed", "Cerrado"),
    ], string="Estado", default="open")

    timesheet_line_ids = fields.One2many(
        "account.analytic.line", "x_periodo_comisiones_id", string="Líneas de Comisiones"
    )
    
    # Campo para indicar si el jefe ha aprobado o rechazado
    approval_state = fields.Selection([
        ('draft', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], string='Aprobación del Jefe', default='draft', tracking=True)
    
    def approve(self):
        """Método para aprobar el período y las líneas asociadas"""
        self.write({'approval_state': 'approved'})
        # Aprobar automáticamente todas las líneas asociadas
        for line in self.timesheet_line_ids:
            line.write({'state': 'approved'})

    def reject(self):
        """Método para rechazar el período y las líneas asociadas"""
        self.write({'approval_state': 'rejected'})
        # Rechazar automáticamente todas las líneas asociadas
        for line in self.timesheet_line_ids:
            line.write({'state': 'rejected'})

class TimesheetPeriodDictado(models.Model):
    _name = "timesheet.period.dictado"
    _description = "Periodo de Timesheet Dictado de Clases (corte 25→24)"

    name = fields.Char(string="Nombre Periodo Dictado Clases", required=True)
    date_start = fields.Date(string="Fecha Inicio del Periodo", required=True)
    date_end = fields.Date(string="Fecha Fin del Periodo", required=True)
    company_id = fields.Many2one("res.company", string="Compañía", default=lambda self: self.env.company)
    state = fields.Selection([
        ("open", "Abierto"),
        ("closed", "Cerrado"),
    ], string="Estado", default="open")

    timesheet_line_ids = fields.One2many(
        "account.analytic.line", "x_periodo_dictado_id", string="Líneas de Dictado de Clases"
    )
    
class TimesheetPeriodBono(models.Model):
    _name = "timesheet.period.bono"
    _description = "Periodo de Timesheet Bono (corte 25→24)"

    name = fields.Char(string="Nombre Periodo Bono", required=True)
    date_start = fields.Date(string="Fecha Inicio del Periodo", required=True)
    date_end = fields.Date(string="Fecha Fin del Periodo", required=True)
    company_id = fields.Many2one("res.company", string="Compañía", default=lambda self: self.env.company)
    state = fields.Selection([
        ("open", "Abierto"),
        ("closed", "Cerrado"),
    ], string="Estado", default="open")

    timesheet_line_ids = fields.One2many(
        "account.analytic.line", "x_periodo_bono_id", string="Líneas de Bonos"
    )
    
    # Campo para indicar si el jefe ha aprobado o rechazado
    approval_state = fields.Selection([
        ('draft', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], string='Aprobación del Jefe', default='draft', tracking=True)
    
    def approve(self):
        """Método para aprobar el período y las líneas asociadas"""
        self.write({'approval_state': 'approved'})
        # Aprobar automáticamente todas las líneas asociadas
        for line in self.timesheet_line_ids:
            line.write({'state': 'approved'})

    def reject(self):
        """Método para rechazar el período y las líneas asociadas"""
        self.write({'approval_state': 'rejected'})
        # Rechazar automáticamente todas las líneas asociadas
        for line in self.timesheet_line_ids:
            line.write({'state': 'rejected'})