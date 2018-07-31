import os
from flask import Flask, render_template, redirect, flash, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
# from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
import subprocess
from forms import LoginForm, InputForm
from config import Config
import logging

app = Flask(__name__)
app.config.from_object(Config)
# bootstrap = Bootstrap(app)

logging.basicConfig(filename='phame.log', level=logging.DEBUG)
logging.debug(app.config['PROJECT_DIRECTORY'])

def upload_files(request, project_dir, ref_dir, work_dir, form):
    """
    uploads files to the proper directories
    updates list of files for reference file combobox
    changes extension of files in work_dir to .contig
    :param request: http request
    :param project_dir: directory where all project files live
    :param ref_dir: directory for complete genome files
    :param work_dir: directory for contigs and PhaME output
    :param form: flask form
    :return:
    """
    os.makedirs(project_dir)
    if 'ref_dir' in request.files:
        if not os.path.exists(ref_dir):
            os.makedirs(ref_dir)
        for file_name in request.files.getlist("ref_dir"):
            filename = secure_filename(file_name.filename)
            file_name.save(os.path.join(ref_dir, filename))

        # update reference file choices from list of reference genomes uploaded
        form.reference_file.choices = [(a.filename, a.filename) for a in request.files.getlist("ref_dir")]
    if 'work_dir' in request.files:
        os.makedirs(work_dir)
        for file_name in request.files.getlist("work_dir"):
            filename = secure_filename(file_name.filename)
            filename = filename.split('.')[:1] + '.contig'
            file_name.save(os.path.join(work_dir, filename))

    if 'reads_file' in request.files:
        reads_file = request.files['reads_file']
        filename = secure_filename(reads_file)
        reads_file.save(os.path.join(ref_dir, filename))


def project_setup(form):
    """
    Create directories and handle file uploads
    :param form:
    :return: reference directory path
    """
    project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], form.project.data)
    ref_dir = os.path.join(project_dir, 'refdir')
    work_dir = os.path.join(project_dir, 'workdir')
    logging.debug(project_dir)
    # project name must be unique
    if os.path.exists(project_dir):
        flash('Project directory already exists')
        return render_template('input.html', title='Phame input', form=form)
    upload_files(request, project_dir, ref_dir, work_dir, form)
    return ref_dir


def create_config_file(form):
    """
    create PhaME config.ctl file
    :param form:
    :return:
    """
    form_dict = request.form.to_dict()
    project = form_dict['project']
    form_dict.pop('csrf_token')
    form_dict['ref_dir'] = '../{0}/refdir/'.format(project)
    form_dict['work_dir'] = '../{0}/workdir'.format(project)
    if len(form.reference_file.data) > 0:
        form_dict['reference_file'] = form.reference_file.data[0]
    content = render_template('phame.tmpl', form=form_dict)
    with open(os.path.join(app.config['PROJECT_DIRECTORY'], project, 'config.ctl'), 'w') as conf:
        conf.write(content)


@app.route('/run/<project>')
def run_phame(project):
    """
    Calls shell script that runs PhaME
    :param project: name of project
    :return: redirects to display view
    """
    try:
        p1 = subprocess.Popen('./docker_run_phame.sh {0}'.format(project), shell=True, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p1.communicate()
        logging.debug(stdout)
        logging.error(stderr)

    except subprocess.CalledProcessError as e:
        logging.error(str(e))
        return "An error occurred while trying to run PhaME: {0}".format(str(e))

    return redirect(url_for('display', project = project))

@app.route('/')
@app.route('/index')
def index():
    user = {'username': 'Migun'}
    return render_template('index.html', title='Home', user=user)


@app.route('/display/<project>', methods=['POST', 'GET'])
def display(project):
    """
    Displays tree output using archeopteryx.js library
    Creates a symlink between PhaME output tree file and static directory in flask directory
    :param project: project name
    :return: renders tree output
    """
    tree_file = '{0}_all.fasttree'.format(project)
    source = os.path.join(app.config['PROJECT_DIRECTORY'], project, 'workdir', 'results', tree_file)
    target = os.path.join(os.path.dirname(__file__), 'static', tree_file)
    if not os.path.exists(target):
        os.symlink(source, target)
    return render_template('tree_output.html', tree= tree_file)


@app.route('/input', methods=['GET', 'POST'])
def input():
    """
    Takes flask form, uploads files, checks parameters to make sure they are correct for PhaME, creates PhaME config
    file
    :return:
    """
    form = InputForm()
    form.reference_file.choices = []
    if request.method == 'POST':
        ref_dir = project_setup(form)

        if form.validate_on_submit():
            # Perform validation based on requirements of PhaME
            if ('1' in form.data_type.data or '2' in form.data_type.data) and 'reference_file' not in request.files:
                flash('You must upload a reference genome if you select Contigs or Reads from Data')
                return render_template('input.html', title='Phame input', form=form)
            # Ensure each fasta file has a corresponding mapping file
            if form.reference.data == '0' or form.reference.data == '2':
                for fname in os.listdir(ref_dir):
                    if fname.endswith('.fa') or fname.endswith('.fasta') or fname.endswith('.fna'):
                        if not os.path.exists(os.path.join(ref_dir, '{0}.{1}'.format(fname.split('.')[0],'gff'))):
                            flash('Each full genome file must have a corresponding .gff file'
                                  ' if random or ANI is selected from Reference')
                            return render_template('input.html', title='Phame input', form=form)

            # Create config file
            create_config_file(form)

            return redirect(url_for('run_phame', project=form.project.data))
    return render_template('input.html', title='Phame input', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}', 'remember_me={}'.format(
            form.username.data, form.remember_me.data
        ))
        return redirect(url_for('login'))
    return render_template('login.html', title='Sign In', form=form)


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
