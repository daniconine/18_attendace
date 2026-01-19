from odoo import models, fields, api
from datetime import datetime
from datetime import timedelta

class ZAttendanceDay(models.Model):
    _inherit = "zattendance.day" 
    
    
    
    permission_id = fields.Many2one( "zleave.permission",
                        string="Solicitud de Permiso",tracking=True, index=True, )

    #####
    @api.model
    def ensure_days(self, employee, date_from, date_to):
        if not employee or not date_from or not date_to:
            return (0, 0)

        ZAttendance = self.sudo().with_context(skip_zattendance_logic=True)
        created = 0

        current = date_from
        while current <= date_to:
            day = ZAttendance.search([
                ('employee_id', '=', employee.id),
                ('date', '=', current),
            ], limit=1)

            if not day:
                ZAttendance.create({
                    'employee_id': employee.id,
                    'date': current,
                })
                created += 1

            current += timedelta(days=1)

        return (created, 0)
        
    #####    
    def _skip_recalcular_logic(self):
        """ Método para bloquear la recalculación de asistencia después de asignar un permiso. """
        for rec in self:
            # Aquí puedes agregar lógica para evitar cualquier recalculación
            rec.planned_presential = 0
            rec.planned_virtual = 0
            rec.actual_presential = 0
            rec.actual_virtual = 0
            rec.diff_attendance = 0  # Reiniciar el cálculo de exceso/defecto de horas

    # Método para manejar la actualización del estado cuando se aprueba un permiso
    def permiso(self, permiso_id):
        """
        Cambia el estado del registro de asistencia a 'permiso' y vincula con la solicitud de permiso.
        Solo se actualiza 'planned_attendance_type' y no 'tipo_asistencia' ya que este es calculado.
        """
        for rec in self:
            if rec.state == "permiso":
                continue  # Si ya está en estado 'permiso', no hacer nada

            # Obtener el tipo de permiso del permiso aprobado
            permiso = self.env['zleave.permission'].browse(permiso_id)
            
            # Asignar el tipo de asistencia correspondiente según el tipo de permiso
            if permiso.type_permission == 'lic_sin_goce':
                tipo_asistencia = 'lic_sin_goce'  # Tipo de asistencia 'Licencia Sin Goce'
            elif permiso.type_permission == 'lic_con_goce':
                tipo_asistencia = 'lic_con_goce'  # Tipo de asistencia 'Licencia Con Goce'
            else:
                tipo_asistencia = 'inasistencia'  # Valor por defecto, si no hay tipo definido

            # Actualizar el campo 'planned_attendance_type' con el tipo de asistencia
            rec.planned_attendance_type = tipo_asistencia

            # Actualizar el estado a 'permiso' y limpiar los campos de planificación
            rec.state = "permiso"
            rec.planned_start = False
            rec.planned_end = False
            rec.planned_presential = 0
            rec.planned_virtual = 0

            # Vincular la solicitud de permiso con el registro de asistencia
            rec.permission_id = permiso_id

            # Bloquear recalcular (si es necesario)
            rec._skip_recalcular_logic()

        return True