# -*- coding: utf-8 -*-
###############################################################################
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime


class OpStudentCourse(models.Model):
    _name = "op.student.course"
    _description = "Estudiante - Programa"
    _inherit = "mail.thread"
    _rec_name = 'roll_number'

    student_id = fields.Many2one('op.student', 'Student',required=True,
                                 ondelete="cascade", tracking=True)
    course_id = fields.Many2one('op.course', 'Programa', required=True, tracking=True)
    #batch_id = fields.Many2one('op.batch', 'Batch', required=True, tracking=True)
    roll_number = fields.Char('N de Matricula',readonly=True, required=True, default="Nuevo")
   
    subject_registration_ids = fields.One2many('op.subject.registration','student_course_id',       
                                 string="Cursos Matriculados", readonly=True)
    
    
     
    state = fields.Selection([('activo', 'Activo'),
                              ('retirado', 'Retirado'),
                              ('egresado', 'Egresado')],
                             string="Estado del Alumno", default="activo",tracking=True)
    
    mode=fields.Selection([('presencial','Presencial'),
                              ('semipresencial', 'Semipresencial'),
                              ('adistancia', 'A Distancia')],
                             string="Modalidad", default="presencial",tracking=True)
    type_roll=fields.Selection([('regular', 'Regular'),
                                ('traslado', 'Traslado'),
                              ('especial', 'Especial')],
                             string="Tipo Matricula", default="regular")
    
    first_roll_date= fields.Date('Fech. Primera Matricula',readonly=True,store=True,
                                 compute="_compute_dates_and_credits", tracking=True)
    last_roll_date= fields.Date('Fech. Ultima Matricula',readonly=True,store=True,
                                compute="_compute_dates_and_credits", tracking=True)
    credits_roll = fields.Integer('Creditos Matriculados',readonly=True,store=True,
                                  compute="_compute_dates_and_credits", tracking=True)   

    tiene_beca = fields.Boolean(string="Tiene Beca", default=False)
    tipo_beca = fields.Selection(
                                [   ('1', 'Beca financiada con fondos públicos nacionales'),
                                    ('2', 'Beca financiada con fondos de la misma universidad'),
                                    ('3', 'Beca financiada con otros fondos (nacionales o internacionales)'),
                                    ('otros', 'Otros')
                                ],string="Tipo de Beca")
    otra_beca = fields.Char(string="Otra Beca", size=150)
    porcentaje_cubierto = fields.Integer(string="Porcentaje Cubierto (%)",
        help="Indicar el porcentaje que cubre la beca sobre el costo total del ciclo (0-100).")
    
    
    #Se extrajo batch
    _sql_constraints = [
        ('unique_name_roll_number_id',
         'unique(roll_number,course_id,student_id)',
         'Número de matrícula y estudiante deben ser únicos!'),
        ('unique_name_roll_number_course_id',
         'unique(roll_number,course_id)',
         'Número de matrícula debe ser único!'),
        ('unique_name_roll_number_student_id',
         'unique(student_id,course_id)',
         'Solo debe ser un registro del alumno por programa.Tampoco puede modficar el registro!'),
    ]

    
    
    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Student Course Details'),
            'template': '/openeducat_core/static/xls/op_student_course.xls'
        }]
    
    
    @api.model
    def create(self, vals):
        # Verificar si ya existe un roll_number en los datos proporcionados
        if not vals.get('roll_number') or vals.get('roll_number') == "Nuevo":
            # Generar automáticamente solo si no se ha proporcionado un roll_number
            current_year = datetime.now().year
            course_id = vals.get('course_id')
            course = self.env['op.course'].browse(course_id)
            program_code = course.code_siu_program.zfill(3) if course.code_siu_program else '000'
            existing_records = self.search_count([('course_id', '=', course_id)])
            sequential_number = f"{existing_records + 1:03d}"  # Correlativo de 3 dígitos
            vals['roll_number'] = f"{current_year}{program_code}{sequential_number}"

        return super(OpStudentCourse, self).create(vals)
    
    #funcion de validacion de beca
    @api.constrains('tiene_beca', 'tipo_beca', 'otra_beca', 'porcentaje_cubierto')
    def _check_beca_constraints(self):
        for record in self:
            # Validar que TIPO_BECA sea obligatorio si TIENE_BECA es True
            if record.tiene_beca and not record.tipo_beca:
                raise ValidationError("El tipo de beca es obligatorio si el estudiante tiene beca.")

            # Validar que OTRA_BECA sea obligatorio si TIPO_BECA es 'otros'
            if record.tipo_beca == 'otros' and not record.otra_beca:
                raise ValidationError("Debe proporcionar una descripción en 'Otra Beca' si el tipo de beca es 'Otros'.")

            # Validar que el porcentaje cubierto sea obligatorio si TIENE_BECA es True
            if record.tiene_beca and (record.porcentaje_cubierto is None or record.porcentaje_cubierto < 0 or record.porcentaje_cubierto > 100):
                raise ValidationError("El porcentaje cubierto debe ser un valor entre 0 y 100 si el estudiante tiene beca.")


    @api.depends('subject_registration_ids')
    def _compute_dates_and_credits(self):
        for record in self:
            registrations = record.subject_registration_ids
            
            # Calcular la fecha de la primera matrícula usando create_date
            create_dates = registrations.mapped('create_date')
            record.first_roll_date = min(create_dates).date() if create_dates else False
            
            # Calcular la fecha de la última matrícula usando create_date
            record.last_roll_date = max(create_dates).date() if create_dates else False
            
            # Calcular el total de créditos matriculados
            record.credits_roll = sum(registration.num_credits for registration in registrations)
    
    
    def action_set_activo(self):
        """Cambiar estado a 'activo'"""
        self.state = 'activo'

    def action_set_retirado(self):
        """Cambiar estado a 'retirado'"""
        self.state = 'retirado'

    def action_set_aprobado(self):
        """Cambiar estado a 'egresado'"""
        self.state = 'egresado'

#########################################################################################

class OpStudent(models.Model):
    _name = "op.student"
    _description = "Student"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {"res.partner": "partner_id"}

    
    first_name = fields.Char('Primer nombre', translate=True)
    #middle_name = fields.Char('Segundo Nombre', size=128)
    apellido_paterno = fields.Char("Apellido Paterno",size=128)
    apellido_materno = fields.Char("Apellido Materno",size=128)
    birth_date = fields.Date('Fec Nacimiento')
    blood_group = fields.Selection([
        ('A+', 'A+'),
        ('B+', 'B+'),
        ('O+', 'O+'),
        ('AB+', 'AB+'),
        ('A-', 'A-'),
        ('B-', 'B-'),
        ('O-', 'O-'),
        ('AB-', 'AB-')
    ], string='Grupo Sanguineo', tracking =True)
    gender = fields.Selection([
        ('masculino', 'Masculino'),
        ('femenino', 'Femenino'),
        ('o', 'Other')
    ], 'Genero', default='masculino')
    nationality = fields.Many2one('res.country', 'Nacionalidad', tracking=True)
    emergency_contact = fields.Many2one('res.partner', 'Contacto emergencia')
    visa_info = fields.Char('Visa Info', size=64)
    id_number = fields.Char('ID Card Number', size=64)
    partner_id = fields.Many2one('res.partner', 'Partner',
                                 ondelete="cascade")
    user_id = fields.Many2one('res.users', 'User', ondelete="cascade")
    gr_no = fields.Char("GR Number", size=20)
    category_id = fields.Many2one('op.category', 'Category')
    course_detail_ids = fields.One2many('op.student.course', 'student_id',
                                        'Detalle Programa',
                                        tracking=True)
    active = fields.Boolean(default=True)

    subject_ids = fields.Many2many(
        'op.subject',
        string='Asignaturas',
        compute='_compute_subject_ids',
        store=True,
        help='Asignaturas en las que está inscrito el estudiante'
    )

    alumno_occupation = fields.Many2one('crm.alumno.occupation', string='Puesto de Trabajo', tracking=True)
    universidad = fields.Many2one('crm.alumno.university', string='Universidad',tracking=True)
    carrera_profesional = fields.Many2one('crm.alumno.carrera.profesional', string='Carrera Profesional'
    ,tracking=True)
    empresa = fields.Many2one(comodel_name='res.partner', string='Empresa',tracking=True)
    country_empresa_id = fields.Many2one("res.country", string="País/Empresa",tracking=True)
    cargo = fields.Char(string='Cargo',tracking=True)
    grado_contacto = fields.Selection(selection=[
        ('bachiller','Bachiller'),
        ('licenciatura','Licenciatura'),
        ('maestria','Maestria'),
        ('doctorado','Doctorado'),
    ], string='Grado Profesional',tracking=True)
    
    email_gerens = fields.Char(string='Email GERENS')
    edad = fields.Char(string='Edad', compute='_compute_edad')
    
        
    _sql_constraints = [
        ('unique_dni', 'unique(dni)', 'El DNI debe ser único para cada alumno.')
    ]
    
    _sql_constraints = [(
        'unique_gr_no',
        'unique(gr_no)',
        'GR Number must be unique per student!'
    )]

    
    #se cambio el sigueitne decorador
    @api.onchange( 'apellido_paterno', 'apellido_materno','first_name') #'middle_name')
    def _onchange_name(self):
        # Inicializamos la lista 'parts' con los campos que no son False y los convertimos en cadenas
        parts = [
            self.apellido_paterno or '',
            self.apellido_materno or '',
            self.first_name or '']
            #self.middle_name or ''

        # Filtrar valores vacíos y concatenar con espacios
        self.name = " ".join(filter(None, parts))
        
    
        
    @api.depends('birth_date')
    def _compute_edad(self):
        for rec in self:
            edad = ''
            if rec.birth_date:
                # Usar fields.Date.today() para manejar fechas sin tiempo
                end_data = fields.Date.today()
                delta = relativedelta(end_data, rec.birth_date)
                # Concatenar años como texto
                edad = str(delta.years) + _(" años")
            rec.edad = edad


    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Students'),
            'template': '/openeducat_core/static/xls/op_student.xls'
        }]

    def create_student_user(self):
        user_group = self.env.ref("base.group_portal") or False
        users_res = self.env['res.users']
        for record in self:
            if not record.user_id:
                user_id = users_res.create({
                    'name': record.name,
                    'partner_id': record.partner_id.id,
                    'login': record.email,
                    'groups_id': user_group,
                    'is_student': True,
                    'tz': self._context.get('tz'),
                })
                record.user_id = user_id

    #funcion que busca las asiganturas en que esta el estudiante
    @api.depends('course_detail_ids.subject_registration_ids.subject_id')
    def _compute_subject_ids(self):
        for student in self:
            # Accede a todas las asignaturas relacionadas a través de los registros de matrícula
            all_subjects = student.course_detail_ids.mapped('subject_registration_ids.subject_id')
            # Asigna los IDs de las asignaturas al campo subject_ids
            student.subject_ids = [(6, 0, all_subjects.ids)]

            
    
                
############################################################################################

class AlumnoOccupation(models.Model):
    _name = 'crm.alumno.occupation'
    _description = 'Alumno Occupation'

    name = fields.Char(string='Puesto de Trabajo')
    
    
class AlumnoUniversity(models.Model):
    _name = 'crm.alumno.university'
    _description = 'Alumno University'

    name = fields.Char(string='Universidad')
    country_id = fields.Many2one('res.country', string='País de Universidad')
    
    
class AlumnoCarreraProfesional(models.Model):
    _name = 'crm.alumno.carrera.profesional'
    _description = 'Alumno Carrera Profesional'

    name = fields.Char(string='Carrera Profesional', required=True)
   