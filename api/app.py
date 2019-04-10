import os
import zipfile
import shutil
from tempfile import mkstemp
import re
import datetime
import glob
import requests
import time
import json
import logging
import pandas as pd
from uuid import uuid4
import ast
from datetime import timedelta

from flask import Flask, render_template, redirect, flash, url_for, request, send_file, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.urls import url_parse
import subprocess
from forms import LoginForm, InputForm, SignupForm, RegistrationForm, SubsetForm, AdminForm
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
import celery.states as states

from database import db_session
from config import Config
from worker import celery
from sqlalchemy import exc

app = Flask(__name__)
app.config.from_object(Config)
login = LoginManager(app)
login.login_view = 'login'
# try:
#     from models import User
# except:
#     pass
from models import User
logging.basicConfig(filename='api.log', level=logging.DEBUG)
logging.debug(app.config['PROJECT_DIRECTORY'])
logging.debug(app.config['STATIC_FOLDER'])


@app.route('/check/<string:task_id>')
def check_task(task_id):
    """
    Endpoint for api that checks task status
    :param task_id: Celery task id
    :return: json of task state
    """
    res = celery.AsyncResult(task_id)
    logging.debug('res state' + res.state)
    if res.state == states.PENDING or res.state == 'PROGRESS':
        result= res.state
    else:

        result = str(res.result)
    logging.debug('result ' + str(result))
    if str(result) is None:
        logging.debug('result is None')
        return render_template('error.html', error={'msg' : 'Task status could not be obtained'})
    return jsonify({'Result': result, 'task_output':json.dumps(res.result)})


@app.route('/wait/<string:task_id>/<project>', methods=['POST', 'GET'])
def wait(task_id, project):
    """
    Creates wait page that displays task status while project is executing
    :param task_id: Celery task id
    :param project: Project name
    :return:
    """
    try:
        return render_template('wait.html', status_url = url_for('check_task', task_id=task_id), project=project, username = current_user.username)
    except exc.TimeoutError as e:
        return render_template('error.html', error={'msg': str(e)})


# @app.route('/status/<project>', methods=['POST', 'GET'])
# def display_status(project):
#     logging.debug('request '+jsonify(request.json))
#     project_status = json.dumps(request.json['data'])
#     return render_template('status.html', project=project, project_status=project_status)

# def timeit(method):
#     def timed(*args, **kw):
#         ts = time.time()
#         result = method(*args, **kw)
#         te = time.time()
#         name = kw.get('log_name', method.__name__.upper())
#         kw['log_time'][name] = te-ts
#
#         return result
#     return timed

@app.route('/runphame/<project>', methods=['POST', 'GET'])
def runphame(project):
    """
    Creates celery task to run PhaME
    :param project: Project name
    :return:
    """
    task = celery.send_task('tasks.run_phame', args = [current_user.username, project])
    logging.debug('task id: {0}'.format(task.id))
    response = check_task(task.id)
    if isinstance(response, dict):
        logging.debug('check task {0}'.format(response.__dict__))
    return redirect(url_for('wait', task_id = task.id, project=project))


@app.route('/get_log/<project>', methods=['GET'])
def get_log(project):
    """
    Endpoint for api call to get project log
    :param project: Project name
    :return: json of log file
    """
    log_file = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, 'workdir', 'results', f'{project}.log')
    if not os.path.exists(log_file):
        return jsonify({'log': 'null'})
    with open(log_file, 'rb') as f:
        f.seek(-2, os.SEEK_END)  # Jump to the second last byte.
        while f.read(1) != b"\n":  # Until EOL is found...
            f.seek(-2, os.SEEK_CUR)  # ...jump back the read byte plus one more.
        last = f.readline()
    return jsonify({'log':str(last)})


@app.route('/num_results_files/<project>', methods=['GET'])
def num_results_files(project):
    results_dir = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, 'workdir', 'results')
    num_files = len(os.listdir(results_dir)) if os.path.exists(results_dir) else 0
    return jsonify({'num_files':num_files})


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


def zip_output_files(project):
    """
    Create a zip file of all files in user's results directory
    :param project: name of project
    :return: zip_name: name of zip file
    """
    zip_name = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, '{0}.zip'.format(project))
    with zipfile.ZipFile(zip_name,  'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, 'workdir', 'results')):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, '..')))
    return zip_name


@app.route('/remove', methods=['POST'])
def remove_files():
    """Remove all of user's uploaded files"""
    file_list = os.listdir(os.path.join(app.config['UPLOAD_DIR'], current_user.username))
    for file_name in file_list:
        os.remove(os.path.join(app.config['UPLOAD_DIR'], current_user.username, file_name))
    file_list = os.listdir(os.path.join(app.config['UPLOAD_DIR'], current_user.username))
    return jsonify({'uploads': sorted(file_list)})


@app.route("/upload", methods=["POST"])
def upload():
    """Handle the upload of a file."""
    form = request.form

    # Create a unique "session ID" for this particular batch of uploads.
    upload_key = str(uuid4())

    # Is the upload using Ajax, or a direct POST by the form?
    is_ajax = False
    if form.get("__ajax", None) == "true":
        is_ajax = True

    # Target folder for these uploads.
    target = os.path.join(app.config['UPLOAD_DIR'], current_user.username)
    if not os.path.exists(target):
        logging.debug(f'creating directory {target}')
        try:
            os.mkdir(target)
        except:
            if is_ajax:
                return ajax_response(False, "Couldn't create upload directory: {}".format(target))
            else:
                return "Couldn't create upload directory: {}".format(target)

    logging.debug("=== Form Data ===")
    for key, value in list(form.items()):
        logging.debug(key, "=>", value)

    for upload in request.files.getlist("file"):
        filename = upload.filename.rsplit("/")[0]
        destination = "/".join([target, filename])
        # logging.debug("Accept incoming file:", filename)
        # logging.debug("Save it to:", destination)
        upload.save(destination)

    if is_ajax:
        return ajax_response(True, upload_key)
    else:
        return redirect(url_for("input"))


def ajax_response(status, msg):
    """
    Checks ajax response for file uploads
    :param status: ajax response status
    :param msg: Message
    :return: json of status and msg
    """
    status_code = "ok" if status else "error"
    return json.dumps(dict(
        status=status_code,
        msg=msg,
    ))


def link_files(project_dir, ref_dir, work_dir, form):
    """
    Symlink files in user's upload directory in web container to project directory in PhaME container
    :param project_dir: Path to project directory
    :param ref_dir: Path to directory with reads and whole genome files
    :param work_dir: Path to directory with contigs and results files
    :param form: Input form
    :return:
    """
    os.makedirs(project_dir, exist_ok=True)
    if len(form.complete_genomes.data) > 0:
        if not os.path.exists(ref_dir):
            os.makedirs(ref_dir)
        # symlink complete genome files
        for file_name in form.complete_genomes.data:
            if os.path.exists(os.path.join(ref_dir, file_name)):
                os.remove(os.path.join(ref_dir, file_name))
            os.symlink(os.path.join(app.config['PHAME_UPLOAD_DIR'], current_user.username, file_name),
                       os.path.join(ref_dir, file_name))
        form.reference_file.choices = [(a, a) for a in form.complete_genomes.data]

    if len(form.reads.data) > 0:
        # symlink reads files
        for file_name in form.reads.data:
            if os.path.exists(os.path.join(ref_dir, file_name)):
                os.remove(os.path.join(ref_dir, file_name))
            os.symlink(os.path.join(app.config['PHAME_UPLOAD_DIR'], current_user.username, file_name),
                       os.path.join(ref_dir, file_name))

    if len(form.contigs.data) > 0:
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
        # symlink contig files
        for file_name in form.contigs.data:
            new_filename = os.path.splitext(file_name)[0] + '.contig'
            if os.path.exists(os.path.join(work_dir, file_name)):
                os.remove(os.path.join(work_dir, new_filename))
            os.symlink(os.path.join(app.config['PHAME_UPLOAD_DIR'], current_user.username, file_name),
                       os.path.join(work_dir, new_filename))


def remove_uploaded_files(project_dir):
    """
    Removes uploaded files if there is a problem creating the project
    :param project_dir: user's project directory
    :return:
    """
    try:
        logging.debug('removing directory {0}'.format(project_dir))
        shutil.rmtree(project_dir)
    except IOError as e:
        logging.error('Could not remove directory {0}: {1}'.format(project_dir, str(e)))


def project_setup(form):
    """
    Checks if project exists and calls function to create symlinks
    :param form: Input form
    :return: project and reference directory paths
    """
    project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, form.project.data)
    ref_dir = os.path.join(project_dir, 'refdir')
    work_dir = os.path.join(project_dir, 'workdir')
    logging.debug(f'project directory: {project_dir}')
    logging.debug(f'reference file: {form.reference_file.data}')
    logging.debug(f'reference file: {form.project.data}')
    # project name for projects that have successfully completed must be unique
    if os.path.exists(os.path.join(work_dir, 'results', f'{form.project.data}.log')) \
        or len(form.reference_file.data) == 0 \
        or len(form.project.data) == 0:
        return None, None
    link_files(project_dir, ref_dir, work_dir, form)
    return project_dir, ref_dir


def get_data_type(options_list):
    # determines what option to enter into config file based on which options were selected in 'Data' from form
    # 0:only complete(F); 1:only contig(C); 2:only reads(R);
    # 3:combination F+C; 4:combination F+R; 5:combination C+R;
    # 6:combination F+C+R;
    if len(options_list) == 1:
        return options_list[0]
    else:
        return str(sum([int(x) + 1 for x in options_list]))


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
        form_dict['reference_file'] = form.reference_file.data
    form_dict['data_type'] = get_data_type(form.data_type.data)
    content = render_template('phame.tmpl', form=form_dict)
    with open(os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, 'config.ctl'), 'w') as conf:
        conf.write(content)


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login for PhaME
    If user is logged in as 'public', they are redirected to the 'projects' page where they
    can view 'public' projects
    :return:
    """
    if current_user.is_authenticated:
        return redirect(url_for('projects')) if current_user.username == 'public' else redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        if not form.public_login.data:
            user = User.query.filter_by(username=form.username.data).first()
            if user is None or not user.check_password(form.password.data):
                flash('Invalid username or password')
                return redirect(url_for('login'))
        else:
            user = User.query.filter_by(username='public').first()
        login_user(user, remember=form.remember_me.data)
        next_page = url_for('projects') if current_user.username == 'public' else request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            # url_for returns /input
            next_page = url_for('projects') if current_user.username == 'public' else url_for('input').split('/')[-1]
        return redirect(url_for(next_page.split('/')[-1]))
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/files', methods=['GET'])
def upload_files_list():
    file_list = os.listdir(os.path.join(app.config['UPLOAD_DIR'], current_user.username))
    return jsonify({'uploads':sorted(file_list)})


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registration for PhaME
    :return:
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db_session.add(user)
        db_session.commit()
        flash('Congratulations, you are now a registered user!')
        os.mkdir(os.path.join(app.config['PROJECT_DIRECTORY'], user.username))
        os.makedirs(os.path.join(app.config['PROJECT_DIRECTORY'], 'uploads', user.username))
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if current_user.username == 'admin':
        form = AdminForm()
        user_list = User.query.all()
        for a in user_list:
            logging.debug(a.username)
        # form.manage_username.choices = [(a.username, a.username) for a in user_list]
        if request.method == 'POST':
            return redirect(url_for('projects', username=form.manage_username.data))
        return render_template('admin.html', user=current_user, form=form)
    else:
        return render_template('profile.html', user=current_user)


@app.route("/success")
def success():
    return "Thank you for signing up!"


@app.route('/subset/<project>', methods=['GET', 'POST'])
@login_required
def subset(project):
    form = SubsetForm()
    project_path = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project)
    new_project = project+'_subset'
    new_project_path = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, new_project)

    ref_dir_files = sorted(os.listdir(os.path.join(project_path, 'refdir')))

    form.subset_files.choices = [(a, a) for a in ref_dir_files if (a.endswith('fna') or a.endswith('fasta'))]

    if request.method == 'POST':
        logging.debug('POST')
        logging.debug('post subset files: {0}'.format(form.subset_files.data))

        # Delete subset directory tree and create new directories
        if os.path.exists(new_project_path):
            shutil.rmtree(new_project_path)
        os.makedirs(os.path.join(new_project_path, 'refdir'))
        os.makedirs(os.path.join(new_project_path, 'workdir'))

        # Change project name in config file
        shutil.copy(os.path.join(project_path, 'config.ctl'), os.path.join(new_project_path))

        # copy selected results directories to new project
        dir_list = ['gaps', 'miscs', 'snps', 'stats', 'temp', 'trees', 'tables']
        for results_dir in dir_list:
            shutil.copytree(os.path.join(project_path, 'workdir', 'results', results_dir),
                            os.path.join(new_project_path, 'workdir', 'results', results_dir))

        #copy files from results directory
        results_files = os.listdir(os.path.join(project_path, 'workdir', 'results'))
        for result_file in results_files:
            if not os.path.isdir(os.path.join(project_path, 'workdir', 'results', result_file)):
                logging.debug(f'result file {result_file}')
                logging.debug(f'isdir {os.path.isdir(result_file)}')
                shutil.copy(os.path.join(project_path, 'workdir', 'results', result_file),
                            os.path.join(new_project_path, 'workdir', 'results'))


        #create new working_list.txt file and copy files
        if not os.path.exists(os.path.join(new_project_path, 'workdir', 'files')):
            os.mkdir(os.path.join(new_project_path, 'workdir', 'files'))
        with open(os.path.join(new_project_path, 'workdir', 'working_list.txt'), 'w') as fp:
            for ref_file in form.subset_files.data:
                fp.write(f'{os.path.splitext(ref_file)[0]}\n')
                if ref_file.endswith('fasta'):
                    ref_file = os.path.splitext(ref_file)[0] + '.fna'
                if os.path.exists(os.path.join(project_path, 'workdir', 'files', ref_file)):
                    shutil.copy(os.path.join(project_path, 'workdir', 'files', ref_file),
                                os.path.join(new_project_path, 'workdir', 'files', ref_file))

        #modify config.ctl file to change project to new name and get reference file name
        fh, abs_path = mkstemp()
        with os.fdopen(fh, 'w') as tmp, open(os.path.join(new_project_path, 'config.ctl'), 'r')as config:
            lines = config.readlines()
            reference_file = ''
            for line in lines:
                if re.search(project, line):
                    tmp.write(re.sub(project, new_project, line))
                elif re.search('data', line):
                    tmp.write('data = 7\n')
                else:
                    tmp.write(line)

                # get name of reference file for form validation
                if re.search('reffile', line):
                    # m = re.search('=\s*(\w*)', line)
                    # reference_file = os.path.splitext(line.split('=')[1].split()[0])[0]
                    reference_file = line.split('=')[1].split()[0]
                    logging.debug('reference line {0}'.format(line))
        shutil.move(abs_path, os.path.join(new_project_path, 'config.ctl'))

        # symlink subset of reference genome files
        for file_name in form.subset_files.data:

            logging.debug(f'file {file_name}')
            os.symlink(os.path.join(app.config['PHAME_UPLOAD_DIR'], current_user.username, file_name),
                       os.path.join(new_project_path, 'refdir', file_name))
                # os.symlink(os.path.join(project_path, 'refdir', file_name), os.path.join(new_project_path, 'refdir', file_name))

        # symlink contig files
        for file_name in os.listdir(os.path.join(project_path, 'workdir')):
            if file_name.endswith('.contig'):
                os.symlink(os.path.join(app.config['PHAME_UPLOAD_DIR'], current_user.username, file_name),
                           os.path.join(new_project_path, 'workdir', file_name))

        if form.validate_on_submit():
            if reference_file not in form.subset_files.data:
                flash('Please include the reference file {0}'.format(reference_file))
                return redirect(url_for('subset', project=project))

            return redirect(url_for('runphame', project=new_project))


    return render_template('subset_input.html', title='Subset Phame input', form=form)


@app.route('/input', methods=['GET', 'POST'])
@login_required
def input():
    """
    Takes flask form, checks parameters to make sure they are correct for PhaME, creates PhaME config
    file
    :return:
    """
    if current_user.username == 'public':
        return redirect(url_for('projects'))

    form = InputForm()
    if not os.path.exists(os.path.join(app.config['UPLOAD_DIR'], current_user.username)):
        os.makedirs(os.path.join(app.config['UPLOAD_DIR'], current_user.username))
    files_list = sorted(os.listdir(os.path.join(app.config['UPLOAD_DIR'], current_user.username)))
    form.reference_file.choices = []
    form.complete_genomes.choices = [(a, a) for a in files_list if (a.endswith('fna') or a.endswith('fasta') or a.endswith('gff'))]
    form.contigs.choices = [(a, a) for a in files_list if a.endswith('contig')]
    form.reads.choices = [(a, a) for a in files_list if a.endswith('fastq')]

    if request.method == 'POST':
        logging.debug(f'request method {request.method}')
        logging.debug(f'reference file {form.reference_file.data}')
        if len(form.project.data) == 0:
            error = 'Please enter a project name'
            return render_template('input.html', title='Phame input', form=form, error=error)
        project_dir, ref_dir = project_setup(form)
        logging.debug(f'ref file {form.reference_file.data}')
        if project_dir is None:
            # project creation failed because there is an existing project that successfully completed
            error = 'Project directory already exists'
            return render_template('input.html', title='Phame input', form=form, error=error)
        if form.validate_on_submit():
            logging.debug(f"data {form.data_type.data}")

            # Perform validation based on requirements of PhaME
            if ('1' in form.data_type.data or '2' in form.data_type.data) and len(form.reference_file.data) == 0:
                error = 'You must upload a reference genome if you select Contigs or Reads from Data'
                remove_uploaded_files(project_dir)
                return render_template('input.html', title='Phame input', form=form, error=error)

            # Ensure each fasta file has a corresponding mapping file if Generate SNPs is yes and 'random' or 'ani'
            if form.cds_snps.data == '1' and (form.reference.data == '0' or form.reference.data == '2'):
                for fname in os.listdir(ref_dir):
                    if fname.endswith('.fa') or fname.endswith('.fasta') or fname.endswith('.fna'):
                        if not os.path.exists(os.path.join(ref_dir, '{0}.{1}'.format(fname.split('.')[0],'gff'))):
                            remove_uploaded_files(project_dir)
                            error = 'Each full genome file must have a corresponding .gff file if '\
                                    '"Generate SNPs from coding regions" is yes and "Reference" is random or ANI'
                            return render_template('input.html', title='Phame input', form=form, error=error)

            # Ensure a reference file is selected if the Reference option selected is 'manual selection'
            if form.reference.data == '1' and len(form.reference_file.data) == 0:
                error = 'You must select a reference genome if you select "manual selection" from the Reference menu'
                remove_uploaded_files(project_dir)
                return render_template('input.html', title='Phame input', form=form, error=error)


            # Create config file
            create_config_file(form)

            return redirect(url_for('runphame', project=form.project.data))

    return render_template('input.html', title='Phame input', form=form)


def get_config_property(project_dir, property):
    value = None
    try:
        with open(os.path.join(project_dir, 'config.ctl'), 'r') as fp:
            lines = fp.readlines()
            for line in lines:
                if re.search(property, line):
                    value = line.split('=')[1].split()[0].strip()
    except IOError as e:
        logging.exception(f'Cannot get config property {property} for project directory {project_dir}')
    return value

@app.route('/download/<project>')
def download(project):
    """
    Calls function to zip project output files and downloads the zipfile when link is clicked
    :param project:
    :return:
    """
    zip_name = zip_output_files(project)
    return send_file(zip_name, mimetype='zip', attachment_filename=zip_name, as_attachment=True)



#
# @app.route('/status/<project>')
# def get_project_status(project):
#     project_log = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, f'{project}.log')
#     if not os.path.exists(project_log):
#         return jsonify({'project_status': 'Failed'})
#     else:
#         with open(project_log, 'r') as fp:
#             for line in fp.readlines():
#                 if 'Tree phylogeny complete.' in line:
#                     return jsonify({'project_status': 'Finished'})


@app.route('/delete', methods=["POST"])
def delete_projects():
    """ Delete project directory files"""
    logging.debug('delete called')
    form = request.form
    projects = form.to_dict(flat=False)
    for project in projects['deleteCheckBox']:
        logging.debug(f'removing project: {project}')
        shutil.rmtree(os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, f'{project}'))
    return redirect(url_for('projects'))


def fix_subset_tables(project, results_dir):
    """
    Copy the tables directory from original directory to subset project directory
    :param project: Name of project
    :param results_dir: Directory with results
    :return:
    """
    try:
        output_files_list = [f'{project}_summaryStatistics.txt', f'{project}_coverage.txt',
                             f'{project}_snp_pairwiseMatrix.txt', f'{project}_genome_lengths.txt']
        logging.debug(f'copying tables for {project}')
        for output_file in output_files_list:
            if not os.path.exists(os.path.join(results_dir, 'tables')):
                os.mkdir(os.path.join(results_dir, 'tables'))
            if os.path.exists(os.path.join(results_dir, output_file)):
                shutil.copy(os.path.join(results_dir, output_file),
                            os.path.join(results_dir, 'tables', output_file))
    except IOError as e:
        logging.debug(f'error for project {project}: {str(e)}')


def get_file_counts(refdir, workdir):
    """
    Get the number of full genome, contigs and reads files
    :param refdir: Reference file directory
    :param workdir: Work file directory
    :return: Number of full, contig and read files
    """
    reads_file_count = len(
        [fname for fname in os.listdir(refdir) if (fname.endswith('.fq') or fname.endswith('.fastq'))])

    contigs_file_count = len([fname for fname in os.listdir(workdir) if fname.endswith('.contig')]) \
        if os.path.exists(workdir) else 0
    full_genome_file_count = len([fname for fname in os.listdir(refdir) if (fname.endswith('.fna') or
                                                                            fname.endswith('.fasta'))])
    return reads_file_count, contigs_file_count, full_genome_file_count


def set_directories(display_user, project):
    """
    Set the directory names for the current project for the current user
    :param project: Project name
    :return: Full paths to project, work, results and reference directories
    """
    project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], display_user, project)
    workdir = os.path.join(project_dir, 'workdir')
    results_dir = os.path.join(workdir, 'results')
    refdir = os.path.join(project_dir, 'refdir')
    return project_dir, workdir, results_dir, refdir


def create_project_summary(project, project_status, num_threads, reads_file_count, contigs_file_count,
                        full_genome_file_count, exec_time, reference_genome):
    """
    Create run summary for project
    Adds a 'delete' field if the user is not 'public'
    :param project: Project name
    :param project_status: Status of project
    :param num_threads: Number of threads used for project
    :param reads_file_count: Number of reads files
    :param contigs_file_count: Number of contig files
    :param full_genome_file_count: Number of full genome files
    :param exec_time: How long it took for project to run
    :param reference_genome: Reference genome file
    :return: project_summary dict
    """
    project_summary = {'# of genomes analyzed': full_genome_file_count + contigs_file_count + reads_file_count,
                       '# of contigs': contigs_file_count,
                       '# of reads': reads_file_count,
                       '# of full genomes': full_genome_file_count,
                       'reference genome used': reference_genome,
                       'project name': project,
                       '# of threads': num_threads,
                       'status': project_status,
                       'execution time(h:m:s)': exec_time
                       }
    if current_user.username != 'public':
        project_summary['delete'] = '<input name="deleteCheckBox" type="checkbox" value={0} unchecked">'.format(
            project)
    return project_summary


def get_all_task_statuses():
    """
    Make a call to the monitor container to get project status for all projects
    :return: api call response as a json
    """
    statuses = requests.get('http://monitor:5555/api/tasks')
    logging.debug(f'status: {statuses.text}')
    logging.debug(f'status json: {statuses.json()}')
    return statuses.json()


def get_project_statuses(display_user):
    """
    Get task statuses for the current users projects
    :return: list of dicts with project names and their states
    """
    task_statuses = get_all_task_statuses()
    logging.debug('task statuses:')
    project_statuses = []
    for task, status in task_statuses.items():
        args_list = ast.literal_eval(status['args'])
        logging.debug(f"task: {task}, {args_list[1]}, {status['state']}")
        if args_list[0] == display_user:
            project_statuses.append({'project': args_list[1], 'state': status['state']})
    return project_statuses


def get_num_threads(project_dir):
    """
    Get the number of threads used for project run
    :param project_dir: Directory for project
    :return: number of threads
    """
    num_threads = get_config_property(project_dir, 'threads')
    if num_threads is None:
        num_threads = 'Unknown'
    return num_threads


def get_exec_time(project_dir):
    """
    Get the project execution time from log file
    :param project_dir: Directory for project
    :return: String representation of time 'h:mm:ss'
    """
    exec_time_string = '0:00:00'
    if os.path.exists(os.path.join(project_dir, 'time.log')):
        with open(os.path.join(project_dir, 'time.log'), 'r') as fp:
            exec_time = float(fp.readline()) / 1000.
            m, s = divmod(exec_time, 60)
            h, m = divmod(m, 60)
            exec_time_string = "%d:%02d:%02d" % (h, m, s)
    return exec_time_string


def get_reference_file(summary_statistics_file):
    """
    Get the name of the reference genome file
    :param summary_statistics_file: Path to summary statistics file
    :return: Reference genome file name
    """
    if os.path.exists(summary_statistics_file) and os.path.getsize(summary_statistics_file) > 0:
        stats_df = pd.read_table(summary_statistics_file, header=None, index_col=0, squeeze=True)
        # logging.debug(f"# reads files {reads_file_count}, # contig files {contigs_file_count}, # full genomes {full_genome_file_count}, ref used {stats_df.loc['Reference used']}")
        reference_genome = stats_df.loc['Reference used']
    else:
        logging.debug('no summary statistics file')
        reference_genome = ''
        # logging.debug(f"# reads files {reads_file_count}, # contig files {contigs_file_count}, # full genomes {full_genome_file_count}")
    return reference_genome


def set_project_status(project_statuses, project, reference_genome, results_dir):
    """
    Set project status: if the status is available from the call to the monitor container, use that
    otherwise, see what results files are present
    :param project_statuses: list of dicts with project names and their states from get_project_statuses
    :param project: Project name
    :param reference_genome: Reference genome file name
    :param results_dir: Path to results directory
    :return: project status ['SUCCESS', 'FAILURE', 'STARTED']
    """

    project_task_status = None
    for status in project_statuses:
        logging.debug(f'project {project} status {status}')
        if status['project'] == project:
            project_task_status = status['state']
    if not project_task_status:
        if not os.path.exists(os.path.join(results_dir, f'{project}.log')) or reference_genome == '':
            project_task_status = 'FAILURE'
        else:
            project_task_status = 'SUCCESS'
    return project_task_status


@app.route('/projects/<username>')
@app.route('/projects')
@login_required
def projects(username=None):
    """
    Displays run summaries and links to user's projects
    :return:
    """
    try:
        pd.set_option('display.max_colwidth', 1000)

        display_user = username if username and current_user.username == 'admin' else current_user.username

        logging.debug(f'display_user {display_user}')
        # list of all projects for this user
        projects_list = [project for project in os.listdir(os.path.join(app.config['PROJECT_DIRECTORY'], display_user))]

        if len(projects_list) == 0 and current_user.username != 'public':
            return redirect(url_for('input'))
        if len(projects_list) == 0 and current_user.username == 'public':
            return redirect(url_for('index'))

        projects_list.sort()

        # list of projects to display
        projects_display_list = []

        project_statuses = get_project_statuses(display_user)

        for project in projects_list:

            try:
                logging.debug(f'{project}')

                project_dir, workdir, results_dir, refdir = set_directories(display_user, project)

                # hack to fix tables for subsetted projects
                if re.search('_subset$', project):
                    fix_subset_tables(project, results_dir)

                summary_statistics_file = os.path.join(results_dir, 'tables',f'{project}_summaryStatistics.txt')

                # create output tables
                reads_file_count, contigs_file_count, full_genome_file_count = get_file_counts(refdir, workdir)

                num_threads = get_num_threads(project_dir)

                exec_time = get_exec_time(project_dir)

                reference_genome = get_reference_file(summary_statistics_file)

                project_task_status = set_project_status(project_statuses, project, reference_genome, results_dir)

                project_summary = create_project_summary(project, project_task_status, num_threads, reads_file_count,
                                    contigs_file_count, full_genome_file_count, exec_time, reference_genome)
                projects_display_list.append(project_summary)
            except:
                logging.exception(f'could not display project {project}')

        run_summary_df = pd.DataFrame(projects_display_list)

        # add delete project checkbox if user is not public
        if current_user.username != 'public':
            run_summary_columns = ['project name', '# of genomes analyzed', '# of contigs', '# of reads',
                                   'reference genome used', '# of threads', 'status', 'execution time(h:m:s)', 'delete']
        else:
            run_summary_columns = ['project name', '# of genomes analyzed', '# of contigs', '# of reads',
                                   'reference genome used', '# of threads', 'status', 'execution time(h:m:s)']

        # Turn project name into a link to the display page if it's finished running successfully
        run_summary_df['project name'] = run_summary_df[['project name', 'status']].apply(
            lambda x: '<a href="/display/{0}/{1}">{1}</a>'.format(display_user, x['project name']) if (x['status'] == 'SUCCESS')
            else x['project name'], axis=1)

        run_summary_df = run_summary_df[run_summary_columns]

        return render_template('projects.html', run_summary=run_summary_df.to_html(escape=False, classes='run summary',
                                                                                   index=False))
    except Exception as e:
        logging.exception(str(e))
        return render_template('error.html', error={'msg' : f'There was a problem displaying projects: {str(e)}'})


def send_email(message, project):
    key = os.environ['API_KEY']
    request_url = os.environ['EMAIL_URL']
    sender = os.environ['SENDER']
    recipient = current_user.email
    logging.info('current_user.email: {0}'.format(recipient))
    results_dir = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, 'workdir', 'results')
    log_file = '{0}.log'.format(project)
    log_fh = open(os.path.join(results_dir, log_file),"rb").read()
    error_file = '{0}.error'.format(project)
    error_fh = open(os.path.join(results_dir, error_file),"rb").read()
    mail_request = requests.post(request_url,
                                 auth=('api', key),
                                 files=[("attachment", log_fh),("attachment", error_fh)],
                                 data={'from': sender,
                                       'to': recipient,
                                       'subject': f'Project {project}',
                                       'text': message
                                       },
                                 )
    logging.debug('from: {0} to: {1} subject: {2} text: {3}'.format(sender, recipient,
                                                                   'Project {0}'.format(project), message))
    logging.debug('log file: {0}, error file: {1}'.format(log_file, error_file))
    logging.info('Status: {0}'.format(mail_request.status_code))
    return mail_request.status_code


@app.route('/notify/<project>', methods=['GET'])
def notify(project):
    logging.debug(f"send notifications: {app.config['SEND_NOTIFICATIONS']}")
    if app.config['SEND_NOTIFICATIONS']:
        try:
            state = send_email('Your project {0} has finished running'.format(project), project)
            logging.info('message sent to {0} for project {1} status code {2}'.format(current_user.email, project, state))
        except os.error as e:
            logging.error(str(e))
    return redirect(url_for('display', username=current_user.username, project=project))

class Switcher(object):
    def table_to_df_name(self, argument):
        switcher = {
            'summaryStatistics': 'df_summaryStatistics',
            'coverage': 'df_coverage',
            'snp_pairwiseMatrix': 'df_snp_pairwiseMatrix',
            'genome_lengths': 'df_genome_lengths'
        }
        return switcher.get(argument, 'Invalid table')

    def table_name_to_df(self, argument):
        method_name = 'df_' + str(argument)
        method = getattr(self, method_name, lambda : "Invalid dataframe")
        return method

    def df_summaryStatistics(self, project, results_dir):
        return pd.read_table(os.path.join(results_dir, '{0}_summaryStatistics.txt'.format(project)), header=None)

    def df_coverage(self, project, results_dir):
        return pd.read_table(os.path.join(results_dir, '{0}_coverage.txt'.format(project)), header=None)

    def df_snp_pairwise(self, project, results_dir):
        return pd.read_table(os.path.join(results_dir, '{0}_snp_pairwiseMatrix.txt'.format(project)), header=None)

    def df_genome_lengths(self, project, results_dir):
        return pd.read_table(os.path.join(results_dir, '{0}_genome_lengths.txt'.format(project)), header=None)

@app.route('/display/<project>', methods=['POST', 'GET'])
@app.route('/display/<username>/<project>', methods=['POST', 'GET'])
def display(project, username = None):
    """
    Displays output from PhaME, including summary statistics, sequence lengths and
    tree output using archeopteryx.js library
    Creates a symlink between PhaME output tree file and static directory in flask directory
    :param project: project name
    :return: renders PhaME output page
    """

    if not username:
        username = current_user.username
    project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], username, project)
    workdir = os.path.join(project_dir, 'workdir')
    results_dir = os.path.join(workdir, 'results')
    refdir = os.path.join(project_dir, 'refdir')
    trees_target_dir = os.path.join(os.path.dirname(__file__), 'static','trees', username)

    if not os.path.exists(workdir):
        error = {'msg': 'Directory does not exist {0}'.format(workdir)}
        return render_template('error.html', error=error)

    # create output tables
    reads_file_count = len(
        [fname for fname in os.listdir(refdir) if (fname.endswith('.fq') or fname.endswith('.fastq'))])
    contigs_file_count = len(
        [fname for fname in os.listdir(workdir) if fname.endswith('.contig')])
    full_genome_file_count = len([fname for fname in os.listdir(refdir) if (fname.endswith('.fna') or
                                                                            fname.endswith('.fasta'))])
    logging.debug('# reads files {0}, # contig files {1}, # full genomes {2}, len(length_df) {3}'.format(
        reads_file_count, contigs_file_count, full_genome_file_count, full_genome_file_count*3-1))

    output_files_list = [f'{project}_summaryStatistics.txt', f'{project}_coverage.txt',
                         f'{project}_snp_pairwiseMatrix.txt', f'{project}_genome_lengths.txt']

    output_tables_list = []
    titles_list = []
    try:
        for output_file in output_files_list:
            if os.path.exists(os.path.join(results_dir, 'tables', output_file)):
                if output_file == f'{project}_summaryStatistics.txt':
                    # run_time = '' if not log_time else log_time[:6]
                    stats_df = pd.read_table(os.path.join(results_dir, 'tables', output_file), header=None, index_col=0)
                    del stats_df.index.name
                    stats_df.columns = ['']
                    run_summary_df = pd.DataFrame({'# of genomes analyzed': reads_file_count + contigs_file_count +
                                                                            full_genome_file_count,
                                                   '# of contigs': contigs_file_count,
                                                   '# of reads': reads_file_count,
                                                   '# of full genomes': full_genome_file_count,
                                                   'reference genome used': stats_df.loc['Reference used'],
                                                   'project name': project
                                                   }
                                                  )
                    output_tables_list.append(run_summary_df.to_html(classes='run_summary'))
                    output_tables_list.append(stats_df.to_html(classes='stats'))
                    titles_list.append('Run Summary')
                    titles_list.append('Summary Statistics')
                elif output_file == f'{project}_coverage.txt':
                    coverage_df = pd.read_table(os.path.join(results_dir, 'tables', output_file))
                    output_tables_list.append(coverage_df.to_html(classes='coverage'))
                    titles_list.append('Genome Coverage')
                elif output_file == f'{project}_snp_pairwiseMatrix.txt':
                    snp_df = pd.read_table(os.path.join(results_dir, 'tables', output_file), sep='\t')
                    snp_df.rename(index=str, columns={'Unnamed: 0': 'Genome'}, inplace=True)
                    snp_df.drop(snp_df.columns[-1], axis=1, inplace=True)
                    snp_df.set_index('Genome', inplace=True)
                    snp_df = snp_df[list(snp_df.columns)].fillna(0.0).astype(int)
                    output_tables_list.append(snp_df.to_html(classes='snp_pairwiseMatrix', index=True))
                    titles_list.append('SNP pairwise Matrix')
                elif output_file == f'{project}_genome_lengths.txt':
                    genome_df = pd.read_table(os.path.join(results_dir, 'tables', output_file))
                    output_tables_list.append(genome_df.to_html(classes='genome_lengths', index=False))
                    titles_list.append('Genome Length')

        # Prepare tree files -- create symlinks between tree files in output directory and flask static directory
        if not os.path.exists(trees_target_dir):
            os.makedirs(trees_target_dir)
        logging.debug(f'tree directory:{trees_target_dir}')
        tree_file_list = [fname for fname in os.listdir(os.path.join(results_dir, 'trees'))
                          if fname.endswith('.fasttree') or fname.endswith('.treefile')
                          or 'bestTree' in fname or 'bipartitions' in fname]

        tree_files = []
        for tree in tree_file_list:
            tree_split = tree.split('/')[-1]
            target = os.path.join(trees_target_dir, tree_split)
            tree_files.append(tree_split)
            logging.debug('fasttree file: trees/{0}'.format(tree_split))
            source = os.path.join(results_dir, 'trees', tree_split)
            if not os.path.exists(target):
                os.symlink(source, target)
            if not os.path.exists(target):
                error = {'msg': 'File does not exists {0}'.format(target)}
                return render_template('error.html', error=error)

        logging.debug(f'results dir: {results_dir}/trees/*.fastree')

        return render_template('display.html',
                               username=username,
                               tables=output_tables_list,
                               titles=titles_list, tree_files=tree_files, project=project)

    except Exception as e:
        logging.exception(str(e))
        return render_template('display.html',
                               tables=[],
                               titles=[], tree_files=[], project=project, file_links=[])



@app.route('/display_tree/<username>/<project>/<tree>')
def display_tree(username, project, tree):
    """
    Creates phylogeny tree using archeopteryx.js
    :param project: Name of project
    :param tree: Name of tree file (.fasttree)
    :return:
    """
    return render_template('tree_output.html', username=username, tree= tree, project=project)


@app.route('/display_file/<project>/<filename>')
def display_file(filename, project):
    """
    Create page to display text file
    :param filename: Name of file to display
    :param project: Project name
    :return:
    """
    with open(os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project,
                                            'workdir', 'results', filename), 'r') as fp:
        content = fp.read()
    return render_template('content.html', text=content)


if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0', port=5090)
    # app.run(debug=True)
