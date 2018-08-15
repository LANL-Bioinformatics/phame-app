import os
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FileField, MultipleFileField, IntegerField, \
    FloatField, SelectField, StringField, widgets, SelectMultipleField, validators
from wtforms.fields.html5 import DecimalRangeField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from models import User

UPLOAD_PATH = 'phame_api01/media'
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class SignupForm(FlaskForm):
    name = StringField('name', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired()])


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class InputForm(FlaskForm):
    boolean_choices = [('0', 'no'), ('1', 'yes')]
    project = StringField(u'Project Name', description='Choose a unique project name')
    data_type = MultiCheckboxField(u'Data', choices=[('0', 'Full'), ('1', 'Contig'), ('2', 'Read')], default='0')
    ref_dir = MultipleFileField(u'Full Genomes', description='.gff/.fasta')
    work_dir = MultipleFileField(u'Upload Contigs')
    reads = SelectField(choices=[('0', 'single reads'), ('1', 'paired reads'), ('2', 'both')], default='2')
    reads_file = MultipleFileField('Upload Reads')
    aligner = SelectField(choices=[('bowtie', 'bowtie'), ('minimap2', 'minimap2')], default='bowtie')
    reference = SelectField(choices=[('0', 'random'), ('1', 'given'), ('2', 'ANI')], default='1')
    reference_file = SelectMultipleField(u'Reference Genome')
    snp_choices = [('0', 'No'), ('1', 'Yes')]
    cds_snps = SelectField(u'Generate SNPs from coding regions',choices=snp_choices, default='0')
    buildSNPdb = SelectField(choices=[('0', 'only align to reference'), ('1', 'build SNP database')], default='0')
    first_time = SelectField(choices=[('0', 'yes'), ('1', 'update existing SNP alignment')], default='1')
    tree = SelectField(u'Tree', choices=[('0', 'no tree'), ('1', 'FastTree'), ('2', 'RAxML'), ('3', 'both')], default='1')
    bootstrap = SelectField(choices=boolean_choices, default='0')
    N = IntegerField('Number of bootstraps', default=100)
    do_select = SelectField(u'Perform selection analysis',choices = boolean_choices, default='0')
    pos_select = SelectField(u'Select analysis algorithm',choices=[('0','PAML'), ('1','HyPhy'), ('1','both')], default='0')
    clean = SelectField(u'Remove intermediate files', choices=boolean_choices, default='0')
    threads = IntegerField('Number of threads', [validators.NumberRange(message='Range should be between 1 and 4.', min=1, max=4)], default=2)
    cutoff = DecimalRangeField(default=0.1)
    submit = SubmitField('Submit')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')
