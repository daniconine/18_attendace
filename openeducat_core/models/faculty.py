# -*- coding: utf-8 -*-
###############################################################################
#Modificado : La fecha de nacimiento bota error si no se llena, no sale el mensaje porque
# se quito el required =True
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class OpFaculty(models.Model):
    _name = "op.faculty"
    _description = "Docente"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {"res.partner": "partner_id"}
    _parent_name = False
    
    partner_id = fields.Many2one('res.partner', 'Partner',
                                 required=True, ondelete="cascade")
    first_name = fields.Char('Primer nombre', translate=True, required=True)
    #middle_name = fields.Char('Segundo Nombre', size=128)
    apellido_paterno = fields.Char("Apellido Paterno",size=128,required=True)
    apellido_materno = fields.Char("Apellido Materno",size=128)
    #last_name = fields.Char('Apellidos', size=128, required=True)
    birth_date = fields.Date('Fecha Nacimiento')
    edad = fields.Char(string='Edad', compute='_compute_edad')
    birth_country = fields.Many2one('res.country',string='País de Nacimiento')
    blood_group = fields.Selection([
        ('A+', 'A+'),
        ('B+', 'B+'),
        ('O+', 'O+'),
        ('AB+', 'AB+'),
        ('A-', 'A-'),
        ('B-', 'B-'),
        ('O-', 'O-'),
        ('AB-', 'AB-')
    ], string='Grupo Sanguíneo', tracking =True)
    gender = fields.Selection([
        ('masculino', 'Masculino'),
        ('femenino', 'Femenino'),
        ('o', 'Other')
    ], 'Genero', default='masculino')
    nationality = fields.Many2one('res.country', 'Nacionalidad')
    emergency_contact = fields.Many2one(
        'res.partner', 'Contacto de Emergencia')
    visa_info = fields.Char('Visa Info', size=64)
    login = fields.Char(
        'Login', related='partner_id.user_id.login', readonly=1)
    last_login = fields.Datetime('Latest Connection', readonly=1,
                                 related='partner_id.user_id.login_date')
   
   
    
    emp_id = fields.Many2one('hr.employee', 'HR Employee')
    main_department_id = fields.Many2one(
        'op.department', 'Departamento Principal',
        default=lambda self:
        self.env.user.dept_id and self.env.user.dept_id.id or False)
    allowed_department_ids = fields.Many2many(
        'op.department', string='Departamentos Permitidos',
        default=lambda self:
        self.env.user.department_ids and self.env.user.department_ids.ids or False)
    active = fields.Boolean(default=True)
    
    ############academico/laboral
    code_faculty = fields.Char(string='Código Docente')
    nivel_academic = fields.Selection([
        ('Grado', 'Grado'),
        ('Magister', 'Magister'),
        ('Doctorado', 'Doctorado')], string='Nivel Académico',tracking=True)
    category_faculty = fields.Selection([
        ('1', 'Ordinario Auxiliar'),
        ('2', 'Ordinario Asociado'),
        ('3', 'Ordinario Principal'),
        ('4', 'Extraordinario'),
        ('5', 'Contratado'),
        ('12', '*Orden de Servicio')], string='Categoría del Docente', default='12',tracking=True)
    dedication_regime= fields.Selection([
        ('0', 'Por temporada'),
        ('2', 'Tiempo Completo'),
        ('1', 'Tiempo Parcial'),
        ('3', 'Dedicación Exclusiva')], string='Regimen de Dedicación',tracking=True)
    fech_ingreso = fields.Date(string ="Fecha de Ingreso",tracking=True)
    fech_inicio = fields.Date(string ="Fecha de Inicio",tracking=True)
    fech_termino = fields.Date(string ="Fecha de Termino",tracking=True)
    has_authority = fields.Selection([
        ('1', 'Si'),
        ('0', 'No')], string='Tiene Cargo de Autoridad')
    position_authority = fields.Selection([
        ('1',"Director"),
        ('2',"Coordinador"),
        ('3',"Jefe"),
        ('4',"Decano"),
        ('5',"Rector"),
        ('6',"Vicerrector/Vicepresidente académico"),
        ('7',"Vicerrector/Vicepresidente de investigación"),
        ('8',"Secretaría General"),
        ('9',"Vicerrector administrativo"),
        ('10',"Otros")], string='Cargo de Autoridad')
    has_disability = fields.Selection([
        ('1', 'Si'),
        ('0', 'No')], string='Cond. de Discapacidad', default = '0')
    disability= fields.Char(string="Tipo de Discapacidad")
    language_native = fields.Selection([
        ('0', 'Español'),
        ('2', 'Aimara'),
        ('5', 'Ashaninka'),
        ('32', 'Quechua')], string='Idioma Nativo')
    language_mother = fields.Selection([
        ('1', 'Si'),
        ('2', 'No')], string='¿Es Lengua Materna?')
    language_foreign = fields.Selection([
        ('4', 'Aleman'),
        ('24', 'Croata'),
        ('30', 'Español'),
        ('35', 'Frances'),
        ('46', 'Ingles'),
        ('50', 'Japones')], string='Idioma Extranjera')
    question1=fields.Selection([
        ('1', 'Si'),
        ('0', 'No')], string='Pregunta 1 (Sunedu)')
    question2=fields.Selection([
        ('1', 'Si'),
        ('0', 'No')], string='Pregunta 2 (Sunedu)')

    empresa = fields.Many2one(comodel_name='res.partner', string='Empresa',tracking=True)
    country_empresa_id = fields.Many2one("res.country", string="País/Empresa",tracking=True)

    @api.constrains('birth_date')
    def _check_birthdate(self):
        for record in self:
            if record.birth_date > fields.Date.today():
                raise ValidationError(_(
                    "La fecha de nacimiento no puede ser la misma actual!"))

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

            
    def create_employee(self):
        for record in self:
            vals = {
                'name': record.name,
                'country_id': record.nationality.id,
                'gender': record.gender,
                'address_home_id': record.partner_id.id
            }
            emp_id = self.env['hr.employee'].create(vals)
            record.write({'emp_id': emp_id.id})
            record.partner_id.write({'partner_share': True, 'employee': True})

    
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
            'label': _('Plantilla para importar Docente'),
            'template': '/openeducat_core/static/xls/op_faculty.xls'
        }]
