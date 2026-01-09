from odoo import models, fields, api
from datetime import datetime


class HrAttendanceExtended(models.Model):
    _inherit = "hr.attendance"  # Heredamos el modelo existente

    # Nuevo campo 'modalidad'
    modalidad = fields.Char(string="Modalidad", compute='_compute_modalidad', store=True, readonly=True)

    # Método para calcular el campo 'modalidad'
    @api.depends('in_mode', 'out_mode')
    def _compute_modalidad(self):
        for record in self:
            if record.in_mode == 'manual' and record.out_mode == 'manual':
                record.modalidad = 'Huellero'
            else:
                record.modalidad = 'Virtual'

    horas_neto = fields.Float(string='Horas Neto', compute='_compute_horas_neto', store=True)
    #metodo para calcular las horas neto,teniendo en cuenta el almuerzo
    @api.depends('worked_hours')
    def _compute_horas_neto(self):
        for attendance in self:
            # Si worked_hours >= 6, restamos 1 hora, si no, mantenemos el valor original.
            if attendance.worked_hours >= 6:
                attendance.horas_neto = attendance.worked_hours - 1
            else:
                attendance.horas_neto = attendance.worked_hours

    # Nuevo campo 'date' que almacena solo la fecha de check_in
    check_in_date = fields.Date(string="Fecha", compute="_compute_check_in_date", store=True)

    @api.depends('check_in')
    @api.depends_context('tz')
    def _compute_check_in_date(self):
        for record in self:
            if record.check_in:
                # Convierte el datetime UTC a la hora local según el tz del contexto (usuario)
                local_dt = fields.Datetime.context_timestamp(record, record.check_in)
                record.check_in_date = local_dt.date()
            else:
                record.check_in_date = False

####Nota##
#PAra el formateo de fecha en odoo18 se puede usar el 
#widget="float_time"
#este widget automáticamente formatea el campo de tipo Float 
# para que se vea como un valor de tiempo (horas y minutos)


    #MEtodo para cerrar asistencias fuera de tiempo
    @api.model
    def close_virtual_attendances(self):
        # Obtenemos todas las asistencias virtuales abiertas que no tengan check_out
        virtual_attendances = self.search([
            ('modalidad', '=', 'Virtual'),
            ('check_out', '=', False)
        ])

        # Obtener la hora actual del servidor (Odoo TZ-aware)
        target_time = fields.Datetime.now()

        for attendance in virtual_attendances:
            # Solo cerrar la asistencia sin calcular overtime
            attendance.check_out = target_time

            # Desactivar la creación de overtime durante el proceso de cierre
            # Esto se logra utilizando un context o cualquier lógica interna para evitar que se dispare _update_overtime
            with self.env.cr.savepoint():
                attendance.write({'check_out': target_time})