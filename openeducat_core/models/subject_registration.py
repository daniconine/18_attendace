# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OpSubjectRegistration(models.Model):
    _name = "op.subject.registration"
    _description = "Matricula de Asignaturas / Cursos"
    _inherit = ["mail.thread"]

    name = fields.Char('Registro', compute='_compute_name', store=True)
    student_course_id = fields.Many2one('op.student.course', string="Matricula del Alumno", required=True)
    roll_number = fields.Char(string="N° Matricula", related='student_course_id.roll_number', store=True, readonly=True)
    academic_term_id = fields.Many2one('op.academic.term', string="Periodo Académico", required=True,tracking=True)
    
    subject_id = fields.Many2one('op.subject', string="Curso/Asignatura", required=True)
    # Campo relacionado para visualizar el ciclo del curso
    cycle = fields.Selection(related='subject_id.cycle', string="Ciclo", store=True, readonly=True)
    num_credits = fields.Integer(related='subject_id.num_credits', string="N° Creditos", store=True, readonly=True)
    state = fields.Selection([('activo', 'Activo'),
                              ('retirado', 'Retirado'),
                              ('aprobado', 'Aprobado'),
                              ('desaprobado', 'Desaprobado')],
                             string="Estado de la Matricula", default="activo",tracking=True)
    
    student_name = fields.Char(
        string="Nombre del Estudiante",
        related='student_course_id.student_id.name',
        store=True,
        readonly=True)
    
    course_name = fields.Char(
        string="Nombre del Programa",
        related='student_course_id.course_id.name',
        store=True,
        readonly=True)
    type_roll = fields.Selection(
        string="Tipo de Matricula",
        related='student_course_id.type_roll',
        store=True,
        readonly=True)
    mode_roll = fields.Selection(
        [('presencial', 'Presencial'),
         ('semipresencial', 'Semipresencial'),
         ('adistancia', 'A Distancia')],
        string="Modalidad de Matrícula",
        readonly=True,
        help="Modalidad registrada en el momento de la matrícula.")
    
    # Restricción SQL para evitar duplicados
    _sql_constraints = [
        (
            'unique_registration',
            'UNIQUE(roll_number, subject_id)',
            'El estudiante ya está matriculado en esta asignatura.'
        )]
    
    
        
    @api.depends('subject_id', 'roll_number')
    def _compute_name(self):
        for record in self:
            # Obtener el code_system de la asignatura relacionada
            code_system = record.subject_id.code_system if record.subject_id else ''
            
            # Concatenar con el roll_number del estudiante
            roll_number = record.roll_number or ''
            
            # Generar el nombre completo
            record.name = f"{code_system}-{roll_number}" if code_system and roll_number else ''
    
    @api.model
    def create(self, vals):
        # Obtener la modalidad desde `op.student.course` y asignarla a `mode_roll`
        student_course = self.env['op.student.course'].browse(vals.get('student_course_id'))
        if student_course:
            vals['mode_roll'] = student_course.mode  # Copiar la modalidad al campo `mode_roll`

        # Crear el registro con la lógica base del modelo
        return super(OpSubjectRegistration, self).create(vals)

        
    def action_set_activo(self):
        """Cambiar estado a 'activo'"""
        self.state = 'activo'

    def action_set_retirado(self):
        """Cambiar estado a 'retirado'"""
        self.state = 'retirado'

    def action_set_aprobado(self):
        """Cambiar estado a 'aprobado'"""
        self.state = 'aprobado'
    
    def action_set_desaprobado(self):
        """Cambiar estado a 'desaprobado'"""
        self.state = 'desaprobado'