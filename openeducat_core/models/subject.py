from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.exceptions import ValidationError

class OpSubject(models.Model):
    _name = "op.subject"
    _inherit = "mail.thread"
    _description = "Curso/Asignatura"

    name = fields.Char('Nombre Completo', compute='_compute_name', store=True)
    code_system = fields.Char('Código Sistema', readonly=True, copy=False)
    nickname= fields.Char('Nombre del Curso', required=True)
    num_credits = fields.Integer('N° Creditos', help='Número creditos del curso.') #reutilizacion de campo
    num_hours_academic = fields.Integer('N° Horas Academicas', help='Número horas academicas del curso. (45min)')
    num_hours_real = fields.Integer('N° Horas Cronologicas', help='Número horas cronologicas del curso. (60min)')
    code_curricular=fields.Char('Código Malla Curricular',)
    
    type = fields.Selection(
        [('theory', 'Theory'), ('practical', 'Practical'),
         ('both', 'Both'), ('other', 'Other')],
        'Type')
    subject_type = fields.Selection(
        [('compulsory', 'Obligatorio'), ('elective', 'Electivo')],
        'Tipo Curso')
    department_id = fields.Many2one(
        'op.department', 'Department',
        default=lambda self:
        self.env.user.dept_id and self.env.user.dept_id.id or False)
    active = fields.Boolean(default=True)

    cycle = fields.Selection([
        ('0', 'Unico Ciclo'),
        ('1', 'Ciclo 1'),
        ('2', 'Ciclo 2'),
        ('3', 'Ciclo 3'),
        ('4', 'Ciclo 4')], string='Ciclo')

    
    course_id = fields.Many2one('op.course',string='Programa', ondelete='cascade',
        help='Programa relacionado con esta asignatura')

    
    registration_ids = fields.One2many(
        'op.subject.registration',  # Modelo relacionado
        'subject_id',               # Campo inverso en el modelo relacionado
        string="Registros de Estudiantes" )
    
    min_score = fields.Integer('Nota Aprobatoria',default= 12, required=True)
    total_sessions = fields.Integer('N° Total de Hrs en Sesiones',default= 20, required=True)
    min_att_total =  fields.Integer('Asitencia Minima(%)',default= 80, required=True)  
     
    is_a_distance = fields.Boolean(string = "Modalidad A Distancia",default=True)
    att_a_virtual = fields.Integer('Min. Asistencia Virtual(%)', default= 80,
                                   help="Porcentaje Minimo de Assitencia Virtual")
    att_a_presencial= fields.Integer('Min. Asistencia Presencial(%)', default= 0,
                                     help="Porcentaje Minimo de Assitencia Presencial")
    
    is_semipresencial = fields.Boolean(string = "Modalidad Semi-Presencial",default=False)
    att_s_virtual = fields.Integer('Min. Asistencia Virtual(%)', default= 60,
                                   help="Porcentaje Minimo de Assitencia Virtual")
    att_s_presencial= fields.Integer('Min. Asistencia Presencial(%)', default= 20,
                                     help="Porcentaje Minimo de Assitencia Presencial")
   
    is_presencial = fields.Boolean(string = "Modalidad Presencial", default=False)
    att_p_virtual = fields.Integer('Min. Asistencia Virtual(%)', default= 0,
                                   help="Porcentaje Minimo de Assitencia Virtual")
    att_p_presencial= fields.Integer('Min. Asistencia Presencial(%)', default= 80,
                                     help="Porcentaje Minimo de Assitencia Presencial")
    
    state = fields.Selection([('activo', 'Activo'),
                              ('cerrado', 'Cerrado')
                              ],string="Estado de la Asignatura", default="activo",tracking=True)
    
    _sql_constraints = [
        ('unique_subject_code',
         'unique(code)', 'Code should be unique per subject!'),
    ]

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Subjects'),
            'template': '/openeducat_core/static/xls/op_subject.xls'
        }]
        
    
    
    @api.model
    def create(self, vals):
        # Obtener las dos últimas cifras del año actual
        current_year = datetime.now().year
        year_suffix = str(current_year)[-2:]

        # Generar el próximo número secuencial para el código
        last_code = self.search([], order='id desc', limit=1).code_system
        if last_code:
            next_seq = int(last_code[2:]) + 1  # Extraer y aumentar el número secuencial
        else:
            next_seq = 1  # Si no hay códigos previos, iniciar desde 1

        # Generar el código con el formato "año+secuencia"
        vals['code_system'] = f"{year_suffix}{str(next_seq).zfill(3)}"

        # Crear el registro
        return super(OpSubject, self).create(vals)

    @api.depends('code_system', 'nickname')
    def _compute_name(self):
        for record in self:
            if record.code_system and record.nickname:
                record.name = f"{record.code_system}-{record.nickname}"
            else:
                record.name = record.nickname or ''
    
    
    
    @api.constrains('min_att_total', 
                'is_a_distance', 'att_a_virtual', 'att_a_presencial',
                'is_semipresencial', 'att_s_virtual', 'att_s_presencial',
                'is_presencial', 'att_p_virtual', 'att_p_presencial')
    def _check_required_fields(self):
        for record in self:
            # Validar que `min_att_total` sea un porcentaje válido
            if record.min_att_total <= 0 or record.min_att_total > 100:
                raise ValidationError(_("El porcentaje mínimo de asistencia total debe estar entre 1% y 100%."))

            # Validar A Distancia
            if record.is_a_distance:
                total_a_distance = record.att_a_virtual + record.att_a_presencial
                if total_a_distance != record.min_att_total:
                    raise ValidationError(_(
                        "La suma de asistencia virtual y presencial para la modalidad A Distancia debe ser igual al porcentaje mínimo de asistencia total (%s%%)."
                    ) % record.min_att_total)

            # Validar Semi-Presencial
            if record.is_semipresencial:
                total_semipresencial = record.att_s_virtual + record.att_s_presencial
                if total_semipresencial != record.min_att_total:
                    raise ValidationError(_(
                        "La suma de asistencia virtual y presencial para la modalidad Semi-Presencial debe ser igual al porcentaje mínimo de asistencia total (%s%%)."
                    ) % record.min_att_total)

            # Validar Presencial
            if record.is_presencial:
                total_presencial = record.att_p_virtual + record.att_p_presencial
                if total_presencial != record.min_att_total:
                    raise ValidationError(_(
                        "La suma de asistencia virtual y presencial para la modalidad Presencial debe ser igual al porcentaje mínimo de asistencia total (%s%%)."
                    ) % record.min_att_total)

