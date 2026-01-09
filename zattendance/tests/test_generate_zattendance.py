from odoo.tests.common import SavepointCase
from odoo import fields

#Problemas con la identificacion de varios trabajadores
#Tener una persona con varios cargos complcia la diferenciciacion
#La ventaja al ser personal de confianza no habria necesidad
#de desarrollo
class TestGenerateZAttendance(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Modelos
        cls.Employee = cls.env['hr.employee']
        cls.Calendar = cls.env['resource.calendar']
        cls.AttLine = cls.env['resource.calendar.attendance']
        cls.ZDay = cls.env['zattendance.day']

        # Crear empleado
        cls.emp = cls.Employee.create({'name': 'Anita Oliver'})

        # Crear calendario con TZ y empleado
        cls.cal = cls.Calendar.create({
            'name': 'Horario Anita',
            'tz': 'America/Lima',
            'employee_id': cls.emp.id,
        })

        # Crear líneas de horario (ejemplo Lunes y Martes)
        cls.AttLine.create({
            'calendar_id': cls.cal.id,
            'dayofweek': '0',          # lunes
            'hour_from': 9.0,
            'hour_to': 19.0,
            'attendance_type': 'presencial',
            'planned_presential': 10,
            'planned_virtual': 0,
            'date_from': fields.Date.from_string('2025-12-01'),
            'date_to': fields.Date.from_string('2025-12-31'),
        })
        cls.AttLine.create({
            'calendar_id': cls.cal.id,
            'dayofweek': '1',          # martes
            'hour_from': 9.0,
            'hour_to': 19.0,
            'attendance_type': 'virtual',
            'planned_presential': 0,
            'planned_virtual': 10,
            'date_from': fields.Date.from_string('2025-12-01'),
            'date_to': fields.Date.from_string('2025-12-31'),
        })

    def test_generate_creates_records_and_fields(self):
        # Ejecutar
        self.cal.action_generate_zattendance()

        # Verificar que creó algo
        records = self.ZDay.search([('employee_id', '=', self.emp.id)])
        self.assertTrue(records, "No se generaron zattendance.day")

        # Tomar un lunes específico del rango (por ejemplo 2025-12-01 es lunes)
        day = self.ZDay.search([
            ('employee_id', '=', self.emp.id),
            ('date', '=', fields.Date.from_string('2025-12-01')),
        ], limit=1)
        self.assertTrue(day, "No se generó el registro para el lunes 2025-12-01")

        # Validar horas planificadas (presencial/virtual)
        self.assertEqual(day.planned_presential, 10)
        self.assertEqual(day.planned_virtual, 0)
        self.assertEqual(day.planned_attendance_type, 'presencial')

        # Validar que planned_start/planned_end existen
        self.assertTrue(day.planned_start)
        self.assertTrue(day.planned_end)

        # Validación mínima de TZ: planned_start debe caer en la MISMA fecha local (sin irse al día anterior)
        # (Esto depende de cómo guardes UTC; aquí harías una conversión a tz y comparas la fecha)
        # Ejemplo (si planned_start es UTC):
        # start_local_date = fields.Datetime.context_timestamp(self.env.user, day.planned_start).date()
        # self.assertEqual(start_local_date, fields.Date.from_string('2025-12-01'))

    def test_generate_updates_existing(self):
        # Crear uno manual antes
        existing = self.ZDay.create({
            'employee_id': self.emp.id,
            'date': fields.Date.from_string('2025-12-02'),
            'planned_presential': 99,
        })

        # Ejecutar de nuevo
        self.cal.action_generate_zattendance()

        # Debe seguir siendo uno
        same = self.ZDay.search([
            ('employee_id', '=', self.emp.id),
            ('date', '=', fields.Date.from_string('2025-12-02')),
        ])
        self.assertEqual(len(same), 1, "Se duplicó el registro en vez de actualizarse")
        self.assertNotEqual(same.planned_presential, 99, "No se actualizó el registro existente")

    def test_generate_no_employee_no_crash(self):
        cal2 = self.Calendar.create({'name': 'Sin empleado', 'tz': 'America/Lima'})
        cal2.action_generate_zattendance()
        # No debe crear nada
        recs = self.ZDay.search([('employee_id', '=', False)])
        self.assertFalse(recs)
