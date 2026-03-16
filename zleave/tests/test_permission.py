# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta

class TestZleavePermission(TransactionCase):

    def setUp(self):
        super(TestZleavePermission, self).setUp()
        # 1. Crear usuarios (Aprobador y Empleado)
        self.group_user = self.env.ref('base.group_user')
        self.user_employee = self.env['res.users'].create({
            'name': 'Empleado Test',
            'login': 'empleado_test',
            'email': 'empleado@test.com',
            'groups_id': [(6, 0, [self.group_user.id])]
        })
        
        self.user_approver = self.env['res.users'].create({
            'name': 'Jefe Test',
            'login': 'jefe_test',
            'email': 'jefe@test.com',
            'groups_id': [(6, 0, [self.group_user.id])]
        })

        # 2. Crear empleados de hr.employee
        self.employee = self.env['hr.employee'].create({
            'name': 'Empleado Test',
            'user_id': self.user_employee.id,
            'work_email': 'empleado@test.com',
        })
        
        self.manager = self.env['hr.employee'].create({
            'name': 'Jefe Test',
            'user_id': self.user_approver.id,
            'work_email': 'jefe@test.com',
        })

        # Asignar jefe directo
        self.employee.parent_id = self.manager

    def test_01_plame_constraints(self):
        """Validar que no se mezclen códigos de suspensión Perfecta e Imperfecta"""
        permission = self.env['zleave.permission']
        
        # Caso error: Licencia con goce pero con código de suspensión perfecta
        with self.assertRaises(ValidationError):
            permission.create({
                'employee_id': self.employee.id,
                'type_permission': 'con_goce',
                'suspension_perfecta': '5', # Error: Debería ser Imperfecta
                'date_from': date.today(),
                'date_to': date.today(),
                'description': 'Test error',
            })

    def test_02_duration_calculation(self):
        """Verificar que el cálculo de días sea inclusivo"""
        date_from = date.today()
        date_to = date_from + timedelta(days=2) # 3 días en total
        
        rec = self.env['zleave.permission'].create({
            'employee_id': self.employee.id,
            'type_permission': 'con_goce',
            'suspension_imperfecta': '26',
            'date_from': date_from,
            'date_to': date_to,
            'description': 'Prueba de 3 días',
        })
        self.assertEqual(rec.duration_days, 3.0, "El cálculo de duración debería ser inclusivo (Desde-Hasta + 1)")

    def test_03_send_without_attachment_fails(self):
        """Verificar que action_send_for_approval lance error si no hay adjuntos"""
        rec = self.env['zleave.permission'].create({
            'employee_id': self.employee.id,
            'type_permission': 'con_goce',
            'suspension_imperfecta': '26',
            'date_from': date.today(),
            'date_to': date.today(),
            'description': 'Sin adjunto',
        })
        
        with self.assertRaises(UserError):
            rec.action_send_for_approval()

    def test_04_approver_security(self):
        """Validar que un usuario diferente al aprobador no pueda ejecutar action_approve"""
        rec = self.env['zleave.permission'].create({
            'employee_id': self.employee.id,
            'type_permission': 'con_goce',
            'suspension_imperfecta': '26',
            'date_from': date.today(),
            'date_to': date.today(),
            'description': 'Test Seguridad',
        })
        
        # Forzar estado enviado (saltando validación de adjuntos para el test)
        rec.write({'state': 'submitted', 'approver_id': self.user_approver.id})

        # Intentar aprobar con el usuario del empleado (que NO es el aprobador)
        with self.assertRaises(UserError):
            rec.with_user(self.user_employee).action_approve()