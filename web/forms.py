import os
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FileField, MultipleFileField, IntegerField, \
    FloatField, SelectField, StringField
from wtforms.validators import DataRequired

UPLOAD_PATH = 'phame_api01/media'
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class InputForm(FlaskForm):
    ref_dir = MultipleFileField(u'Reference Directory')
    work_dir = MultipleFileField(u'Working Directory')
    reference_file = FileField(u'Reference File')
    reference = SelectField(choices=[('0', 'random'), ('1', 'given'), ('2', 'ANI')], default='0')
    project = StringField(default='ecoli')
    cds_snps = SelectField(choices=[('0', 'no cds SNPS'), ('1', 'cds SNPs')], default='0')
    buildSNPdb = SelectField(choices=[('0', 'only align to reference'), ('1', 'build SNP database')], default='0')
    first_time = SelectField(choices=[('0', 'yes'), ('1', 'update existing SNP alignment')], default='0')
    data = SelectField(choices=[('0', 'F'), ('1', 'C'), ('2', 'R'), ('3', 'F+C'), ('4', 'F+R'), ('5', 'C+R'), ('6', 'F+C+R')], default='0')
    reads = SelectField(choices=[('0', 'single reads'), ('1', 'paired reads'), ('2', 'both')], default='0')
    aligner = SelectField(choices=[('bowtie', 'bowtie'), ('FastTree', 'FastTree'), ('minimap2', 'minimap2')], default='bowtie')
    tree = SelectField(choices=[('0', 'no tree'), ('1', 'FastTree'), ('2', 'RAxML'), ('3', 'both')], default='0')
    boolean_choices = [('0', 'no'), ('1', 'yes')]
    bootstrap = SelectField(choices=boolean_choices, default='0')
    N = IntegerField(default=100)
    pos_select = SelectField(choices=[('0','no'), ('1','PAML'), ('2','HyPhy'), ('3','both')], default='0')
    code = SelectField(choices=[('0','Bacteria'), ('1','Virus')], default='0')
    clean = SelectField(choices=boolean_choices, default='0')
    threads = IntegerField(default=2)
    cutoff = FloatField(default=0.1)
    submit = SubmitField('Submit')


