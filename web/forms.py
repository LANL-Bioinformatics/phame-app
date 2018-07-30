import os
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FileField, MultipleFileField, IntegerField, \
    FloatField, SelectField, StringField, widgets, SelectMultipleField
from wtforms.fields.html5 import DecimalRangeField
from wtforms.validators import DataRequired

UPLOAD_PATH = 'phame_api01/media'
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')
class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class InputForm(FlaskForm):
    boolean_choices = [('0', 'no'), ('1', 'yes')]
    project = StringField(u'Project Name', default='t4')
    data_type = MultiCheckboxField(u'Data', choices=[('0', 'F'), ('1', 'C'), ('2', 'R')], default='0')
    ref_dir = MultipleFileField(u'Full Genomes', description='.gff/.fasta')
    work_dir = MultipleFileField(u'Contigs')
    reads = SelectField(choices=[('0', 'single reads'), ('1', 'paired reads'), ('2', 'both')], default='2')
    reads_file = MultipleFileField('Upload Reads')
    aligner = SelectField(choices=[('bowtie', 'bowtie'), ('FastTree', 'FastTree'), ('minimap2', 'minimap2')], default='bowtie')
    reference = SelectField(choices=[('0', 'random'), ('1', 'given'), ('2', 'ANI')], default='1')
    reference_file = SelectMultipleField(u'Reference Genome')
    cds_snps = SelectField(u'CDS SNPS',choices=boolean_choices, default='1')
    buildSNPdb = SelectField(choices=[('0', 'only align to reference'), ('1', 'build SNP database')], default='0')
    first_time = SelectField(choices=[('0', 'yes'), ('1', 'update existing SNP alignment')], default='1')
    tree = SelectField(u'Tree', choices=[('0', 'no tree'), ('1', 'FastTree'), ('2', 'RAxML'), ('3', 'both')], default='1')
    bootstrap = SelectField(choices=boolean_choices, default='0')
    N = IntegerField('Number of bootstraps', default=100)
    do_select = SelectField(u'Selection Analysis',choices = boolean_choices, default='0')
    pos_select = SelectField(u'Algorithm',choices=[('0','PAML'), ('1','HyPhy'), ('1','both')], default='0')
    clean = SelectField(choices=boolean_choices, default='0')
    threads = IntegerField(default=2)
    cutoff = DecimalRangeField(default=0.1)
    submit = SubmitField('Submit')


