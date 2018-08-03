import os
import zipfile
import shutil
import datetime
import glob
from flask import Flask, render_template, redirect, flash, url_for, request, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
# from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
import subprocess
from forms import LoginForm, InputForm, SignupForm
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
# from database import db_session
from config import Config
import logging
import pandas as pd

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db) # this
login = LoginManager(app)
# bootstrap = Bootstrap(app)

from models import *
logging.basicConfig(filename='phame.log', level=logging.DEBUG)
logging.debug(app.config['PROJECT_DIRECTORY'])

def zip_output_files(project):
    zip_name = os.path.join(app.config['PROJECT_DIRECTORY'], project, '{0}.zip'.format(project))
    with zipfile.ZipFile(zip_name,  'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(os.path.join(app.config['PROJECT_DIRECTORY'], project, 'workdir', 'results')):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(app.config['PROJECT_DIRECTORY'], project, '..')))
    return zip_name

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

def remove_uploaded_files(project_dir):
    try:
        shutil.rmtree(project_dir)
    except IOError as e:
        logging.error('Could not remove directory {0}: {1}'.format(project_dir, str(e)))

def project_setup(form):
    """
    Create directories and handle file uploads
    :param form:
    :return: project and reference directory paths
    """
    project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], form.project.data)
    ref_dir = os.path.join(project_dir, 'refdir')
    work_dir = os.path.join(project_dir, 'workdir')
    logging.debug('project directory: {0}'.format(project_dir))
    # project name must be unique
    if os.path.exists(project_dir):
        return None, None
    upload_files(request, project_dir, ref_dir, work_dir, form)
    return project_dir, ref_dir


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
        if len(stderr) > 0:
            error = {'msg':stderr}
            return render_template('error.html', error=error)

    except subprocess.CalledProcessError as e:
        logging.error(str(e))
        return "An error occurred while trying to run PhaME: {0}".format(str(e))

    return redirect(url_for('display', project = project))

@app.route('/')
@app.route('/index')
def index():
    user = {'username': 'Migun'}
    return render_template('index.html', title='Home', user=user)


@app.route('/projects')
def projects_list():
    # projects = [{'project':project,'path':os.path.join(app.config['PROJECT_DIRECTORY'], project)} for project in os.listdir(app.config['PROJECT_DIRECTORY'])]
    projects = [project for project in os.listdir(app.config['PROJECT_DIRECTORY'])]
    # projects = {'projects': projects_list}
    return render_template('projects.html', projects=projects)


@app.route('/display/<project>', methods=['POST', 'GET'])
def display(project):
    """
    Displays tree output using archeopteryx.js library
    Creates a symlink between PhaME output tree file and static directory in flask directory
    :param project: project name
    :return: renders tree output
    """
    project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], project)
    results_dir = os.path.join(project_dir, 'workdir', 'results')
    refdir = os.path.join(app.config['PROJECT_DIRECTORY'], project, 'refdir')
    target_dir = os.path.join(os.path.dirname(__file__), 'static')
    summary_stats_file = '{0}_summaryStatistics.txt'.format(project)
    output_tables_list, titles_list = [], []
    if os.path.exists(os.path.join(results_dir, summary_stats_file)):
        stats_df = pd.read_table(os.path.join(results_dir, summary_stats_file), header=None)
        count = len([fname for fname in os.listdir(refdir) if (fname.endswith('.fna') or fname.endswith('.fasta'))])
        lengths_df = stats_df.iloc[:count-1].drop(1, axis=1)
        lengths_df.columns = ['sequence name', 'total length']
        lengths_df = lengths_df.set_index('sequence name')
        ref_stats = stats_df.iloc[count:].drop(2, axis=1)
        ref_stats = ref_stats.set_index(0)
        ref_stats.columns = ['']
        del ref_stats.index.name
        output_tables_list = [lengths_df.to_html(classes='lengths'), ref_stats.to_html(classes='ref_stats')]
        titles_list = ['na', 'sequence lengths', 'stats']
    if os.path.exists(os.path.join(results_dir, 'CDScoords.txt')):
        coords_df = pd.read_table(os.path.join(results_dir, 'CDScoords.txt'), header=None)
        coords_df.columns = ['sequence name', 'begin', 'end', 'type']
        coords_df = coords_df.set_index('sequence name')
        output_tables_list.append(coords_df.to_html(classes='coords'))
        titles_list.append('coordinates')


    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    tree_file_list = [fname for fname in os.listdir(results_dir) if fname.endswith('.fasttree')]

    tree_files = []
    for tree in tree_file_list:
        tree_split = tree.split('/')[-1]
        target = os.path.join(target_dir, 'trees', tree_split)
        # tree_files.append('trees/{0}'.format(tree_split))
        tree_files.append(tree_split)
        logging.debug('fasttree file: trees/{0}'.format(tree_split))
        source = os.path.join(results_dir, tree_split)
        if not os.path.exists(target):
            os.symlink(source, target)
        if not os.path.exists(target):
            error = {'msg': 'File does not exists {0}'.format(target)}
            return render_template('error.html', error=error)

    logging.debug('results dir: {0}/*.fastree'.format(results_dir))

    return render_template('table_output.html',
                    tables=output_tables_list,
                    titles=titles_list, tree_files=tree_files, project=project)



@app.route('/display/<project>/<tree>')
def display_tree(project, tree):
    return render_template('tree_output.html', tree= tree, project=project)


@app.route('/download/<project>')
def download(project):
    zip_name = zip_output_files(project)
    return send_file(zip_name, mimetype='zip', attachment_filename=zip_name, as_attachment=True)


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
        project_dir, ref_dir = project_setup(form)
        if project_dir is None:
            error = 'Project directory already exists'
            return render_template('input.html', title='Phame input', form=form, error=error)
        if form.validate_on_submit():
            # Perform validation based on requirements of PhaME
            if ('1' in form.data_type.data or '2' in form.data_type.data) and len(form.reference_file.data) == 0:
                error = 'You must upload a reference genome if you select Contigs or Reads from Data'
                remove_uploaded_files(project_dir)
                return render_template('input.html', title='Phame input', form=form, error=error)
            # Ensure each fasta file has a corresponding mapping file
            if form.reference.data == '0' or form.reference.data == '2':
                for fname in os.listdir(ref_dir):
                    if fname.endswith('.fa') or fname.endswith('.fasta') or fname.endswith('.fna'):
                        if not os.path.exists(os.path.join(ref_dir, '{0}.{1}'.format(fname.split('.')[0],'gff'))):
                            remove_uploaded_files(project_dir)
                            error = 'Each full genome file must have a corresponding .gff file if random or ANI is ' \
                                    'selected from Reference'
                            return render_template('input.html', title='Phame input', form=form, error=error)

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

# @app.route('/register', methods=['GET', 'POST'])
# def signup():
#     form = SignupForm()
#     if form.validate_on_submit():
#         signup = Signups(name=form.name.data, email=form.email.data, date_signed_up=datetime.datetime.now())
#         db_session.add(signup)
#         db_session.commit()
#         return redirect(url_for('success'))
#     return render_template('signup.html', form=form)

@app.route("/success")
def success():
    return "Thank you for signing up!"
if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
