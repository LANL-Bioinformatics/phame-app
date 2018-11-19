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
from IPython.display import HTML

from flask import Flask, render_template, redirect, flash, url_for, request, send_file, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.urls import url_parse
import subprocess
from forms import LoginForm, InputForm, SignupForm, RegistrationForm, SubsetForm
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
try:
    from models import User
except:
    pass

logging.basicConfig(filename='api.log', level=logging.DEBUG)
logging.debug(app.config['PROJECT_DIRECTORY'])
logging.debug(app.config['STATIC_FOLDER'])

@app.route('/add/<int:param1>/<int:param2>')
def add(param1, param2):
    task = celery.send_task('tasks.add', args=[param1, param2], kwargs={})
    response = "<a href='{url}'>check status of {id} </a>".format(id=task.id,
                                                                  url=url_for('check_task', task_id=task.id, external=True))
    return response


@app.route('/check/<string:task_id>')
def check_task(task_id):
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
    try:
        return render_template('wait.html', status_url = url_for('check_task', task_id=task_id), project=project)
    except exc.TimeoutError as e:
        return render_template('error.html', error={'msg': str(e)})


@app.route('/status/<project>', methods=['POST', 'GET'])
def display_status(project):
    logging.debug('request '+jsonify(request.json))
    project_status = json.dumps(request.json['data'])
    return render_template('status.html', project=project, project_status=project_status)


@app.route('/runphame/<project>', methods=['POST', 'GET'])
def runphame(project):
    log_time_data = {}
    task = celery.send_task('tasks.run_phame', args = [current_user.username, project])
    logging.debug('task id: {0}'.format(task.id))
    response = check_task(task.id)
    if isinstance(response, dict):
        logging.debug('check task {0}'.format(response.__dict__))

    return redirect(url_for('wait', task_id = task.id, project=project))


@app.route('/num_results_files/<project>', methods=['GET'])
def num_results_files(project):
    results_dir = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, 'workdir', 'results')
    num_files = len(os.listdir(results_dir)) if os.path.exists(results_dir) else 0
    return jsonify({'num_files':num_files})


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        name = kw.get('log_name', method.__name__.upper())
        kw['log_time'][name] = te-ts

        return result
    return timed

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
            filename = os.path.splitext(filename)[0] + '.contig'
            file_name.save(os.path.join(work_dir, filename))

    if 'reads_file' in request.files:
        for reads_file in request.files.getlist('reads_file'):
            filename = secure_filename(reads_file.filename)
            reads_file.save(os.path.join(ref_dir, filename))


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
    Create directories and handle file uploads
    :param form:
    :return: project and reference directory paths
    """
    # project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], current_user, form.project.data)
    project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, form.project.data)
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
    with open(os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, 'config.ctl'), 'w') as conf:
        conf.write(content)

def check_files(form):
    """
    Check to make sure that for each data type the corresponding files have been uploaded as well
    :param form:
    :return: error: String containing file types that need to be uploaded
    """
    error = ''
    if '0' in form.data_type.data and 'ref_dir' not in request.files:
        error += 'Please select full genome files...'
    if '1' in form.data_type.data and 'work_dir' not in request.files:
        error += 'Please select contig files...'
    if '2' in form.data_type.data and 'reads_file' not in request.files:
        error += 'Please select reads file...'
    return error


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
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
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
def files_list():
    return jsonify(os.listdir(os.path.join(app.config['PROJECT_DIRECTORY'], 'uploads', current_user.username)))


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

@app.route('/profile')
def profile():
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

    # Get list of reference genome choices
    working_list_file = os.path.join(project_path, 'workdir', 'working_list.txt')
    with open(working_list_file, 'r') as config:
        lines = config.readlines()
        reference_genome_files = []
        for line in lines:
            reference_genome_files.append((line.strip(), line.strip()))
        logging.debug('genome choices {0}'.format(reference_genome_files))
    form.subset_files.choices = reference_genome_files

    if request.method == 'POST':
        logging.debug('POST')
        logging.debug('post subset files: {0}'.format(form.subset_files.data))
        logging.debug('working list file: {0}'.format(working_list_file))

        # Delete subset directory tree and create new directories
        if os.path.exists(new_project_path):
            shutil.rmtree(new_project_path)
        os.makedirs(os.path.join(new_project_path, 'refdir'))
        os.makedirs(os.path.join(new_project_path, 'workdir'))

        # Change project name in config file
        shutil.copy(os.path.join(project_path, 'config.ctl'), os.path.join(new_project_path))
        fh, abs_path = mkstemp()
        with os.fdopen(fh, 'w') as tmp, open(os.path.join(new_project_path, 'config.ctl'), 'r')as config:
            lines = config.readlines()
            reference_file = ''
            for line in lines:
                if re.search(project, line):
                    tmp.write(re.sub(project, new_project, line))
                else:
                    tmp.write(line)

                # get name of reference file for form validation
                if re.search('reffile', line):
                    m = re.search('=\s*(\w*)', line)
                    reference_file = m.group(1)
                    logging.debug('reference file {0}'.format(reference_file))
        shutil.move(abs_path, os.path.join(new_project_path, 'config.ctl'))

        # symlink subset of reference genome files
        for file_name in os.listdir(os.path.join(project_path, 'refdir')):
            if file_name.split('.')[0] in form.subset_files.data:
                os.symlink(os.path.join(project_path, 'refdir', file_name), os.path.join(new_project_path, 'refdir', file_name))

        # symlink contig files
        for file_name in os.listdir(os.path.join(project_path, 'workdir')):
            if file_name.endswith('.contig'):
                os.symlink(os.path.join(project_path, 'workdir', file_name),
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
    Takes flask form, uploads files, checks parameters to make sure they are correct for PhaME, creates PhaME config
    file
    :return:
    """
    if current_user.username == 'public':
        return redirect(url_for('projects'))

    form = InputForm()
    form.reference_file.choices = []
    if request.method == 'POST':
        project_dir, ref_dir = project_setup(form)
        if project_dir is None:
            error = 'Project directory already exists'
            return render_template('input.html', title='Phame input', form=form, error=error)
        if form.validate_on_submit():
            # Perform validation based on requirements of PhaME
            files_error = check_files(form)
            if len(files_error) > 0:
                return render_template('input.html', title='Phame input', form=form, error=files_error)

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

            # Ensure a reference file is selected if the Reference option selected is 'given'
            if form.reference.data == '1' and len(form.reference_file.data) == 0:
                error = 'You must select a reference genome if you select "given" in from the Reference menu'
                remove_uploaded_files(project_dir)
                return render_template('input.html', title='Phame input', form=form, error=error)

            # Create config file
            create_config_file(form)

            return redirect(url_for('runphame', project=form.project.data))
        else:
            remove_uploaded_files(project_dir)

    return render_template('input.html', title='Phame input', form=form)



@app.route('/display/<project>/<tree>')
def display_tree(project, tree):
    """
    Creates phylogeny tree using archeopteryx.js
    :param project: Name of project
    :param tree: Name of tree file (.fasttree)
    :return:
    """
    return render_template('tree_output.html', tree= tree, project=project)


@app.route('/download/<project>')
def download(project):
    """
    Calls function to zip project output files and downloads the zipfile when link is clicked
    :param project:
    :return:
    """
    zip_name = zip_output_files(project)
    return send_file(zip_name, mimetype='zip', attachment_filename=zip_name, as_attachment=True)


@app.route('/display_file/<project>/<filename>')
def display_file(filename, project):
    with open(os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project,
                                            'workdir', 'results', filename), 'r') as fp:
        content = fp.read()
    return render_template('content.html', text=content)


@app.route('/projects')
@login_required
def projects():
    """
    Displays links to user's projects
    :return:
    """
    try:
        pd.set_option('display.max_colwidth', 1000)
        projects = [project for project in os.listdir(os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username))]
        projects.sort()
        projects_list = []
        for project in projects:
            project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project)
            workdir = os.path.join(project_dir, 'workdir')
            results_dir = os.path.join(workdir, 'results')
            refdir = os.path.join(project_dir, 'refdir')
            summary_statistics_file = os.path.join(results_dir, 'tables','{0}_summaryStatistics.txt'.format(project))
            if os.path.exists(summary_statistics_file):
                logging.debug(f'{project}')
                # create output tables
                reads_file_count = len(
                    [fname for fname in os.listdir(refdir) if (fname.endswith('.fq') or fname.endswith('.fastq'))])
                contigs_file_count = len(
                    [fname for fname in os.listdir(workdir) if fname.endswith('.contig')])
                full_genome_file_count = len([fname for fname in os.listdir(refdir) if (fname.endswith('.fna') or
                                                                                        fname.endswith('.fasta'))])
                stats_df = pd.read_table(summary_statistics_file, header=None, index_col=0, squeeze=True)
                logging.debug(f"stats {stats_df}")
                logging.debug(f"# reads files {reads_file_count}, # contig files {contigs_file_count}, # full genomes {full_genome_file_count}, ref used {stats_df.loc['Reference used']}")
                projects_list.append({'# of genomes analyzed': reads_file_count + contigs_file_count +
                                                                        full_genome_file_count,
                                               '# of contigs': contigs_file_count,
                                               '# of reads': reads_file_count,
                                               '# of full genomes': full_genome_file_count,
                                               'reference genome used': stats_df.loc['Reference used'],
                                               'project name': project
                                               })

        run_summary_df = pd.DataFrame(projects_list)
        run_summary_df['project name'] = run_summary_df['project name'].apply(lambda x:'<a href="/display/{0}">{0}</a>'.format(x))
        run_summary_df = run_summary_df[['project name', '# of genomes analyzed', '# of contigs', '# of reads', 'reference genome used']]
        return render_template('projects.html', run_summary=run_summary_df.to_html(escape=False, classes='run summary',index=False))
    except Exception as e:
        logging.exception(str(e))
        return render_template('error.html', error={'msg' : f'There was a problem displaying projects: {str(e)}'})

def send_email_message(message, project):
    SENDMAIL = "/usr/sbin/sendmail"  # sendmail location

    p = os.popen("%s -t" % SENDMAIL, "w")
    p.write("To: {0}\n".format('mflynn@lanl.gov'))
    p.write("Subject: Project {0} has finished\n".format(project))
    p.write("\n")# blank line separating headers from body
    p.write("{0}\n".format(message))
    sts = p.close()
    return sts


def send_mailgun(message, project):
    key = '***REMOVED***'
    email_domain = 'mail.edgebioinformatics.org'
    recipient = current_user.email
    logging.info('current_user.email: {0}'.format(recipient))
    request_url = 'https://api.mailgun.net/v3/{0}/messages'.format(email_domain)
    results_dir = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project, 'workdir', 'results')
    log_file = '{0}.log'.format(project)
    log_fh = open(os.path.join(results_dir, log_file),"rb").read()
    error_file = '{0}.error'.format(project)
    error_fh = open(os.path.join(results_dir, error_file),"rb").read()
    mail_request = requests.post(request_url,
                                 auth=('api', key),
                                 files=[("attachment", log_fh),("attachment", error_fh)],
                                 data={'from': 'donotreply@edgebioinformatics.org',
                                       'to': recipient,
                                       'subject': 'Project {0}'.format(project),
                                       'text': message
                                       },
                                 # headers={'Content-type': 'multipart/form-data;'},
                                 )
    logging.debug('from: {0} to: {1} subject: {2} text: {3}'.format('donotreply@edgebioinformatics.org', recipient,
                                                                   'Project {0}'.format(project), message))
    logging.debug('log file: {0}, error file: {1}'.format(log_file, error_file))
    logging.info('Status: {0}'.format(mail_request.status_code))
    return mail_request.status_code


@app.route('/notify/<project>', methods=['GET'])
def notify(project):
    state = None
    try:
        state = send_mailgun('Your project {0} has finished running'.format(project), project)
        logging.info('message sent to {0} for project {1} status code {2}'.format(current_user.email, project, state))
    except os.error as e:
        logging.error(str(e))
    return redirect(url_for('display', project=project))

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
@app.route('/display/<project>/<log_time>', methods=['POST', 'GET'])
def display(project, log_time=None):
    """
    Displays output from PhaME, including summary statistics, sequence lengths and
    tree output using archeopteryx.js library
    Creates a symlink between PhaME output tree file and static directory in flask directory
    :param project: project name
    :return: renders PhaME output page
    """

    project_dir = os.path.join(app.config['PROJECT_DIRECTORY'], current_user.username, project)
    workdir = os.path.join(project_dir, 'workdir')
    results_dir = os.path.join(workdir, 'results')
    refdir = os.path.join(project_dir, 'refdir')
    target_dir = os.path.join(os.path.dirname(__file__), 'static')

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

    output_files_list = ['{0}_summaryStatistics.txt'.format(project), '{0}_coverage.txt'.format(project),
                         '{0}_snp_pairwiseMatrix.txt'.format(project), '{0}_genome_lengths.txt'.format(project)]

    output_tables_list = []
    titles_list = []
    try:
        for output_file in output_files_list:
            if os.path.exists(os.path.join(results_dir, 'tables', output_file)):
                if output_file == '{0}_summaryStatistics.txt'.format(project):
                    run_time = '' if not log_time else log_time[:6]
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
                elif output_file == '{0}_coverage.txt'.format(project):
                    coverage_df = pd.read_table(os.path.join(results_dir, 'tables', output_file))
                    output_tables_list.append(coverage_df.to_html(classes='coverage'))
                    titles_list.append('Genome Coverage')
                elif output_file == '{0}_snp_pairwiseMatrix.txt'.format(project):
                    snp_df = pd.read_table(os.path.join(results_dir, 'tables', output_file), sep='\t')
                    snp_df.rename(index=str, columns={'Unnamed: 0':''}, inplace=True)
                    snp_df.drop(snp_df.columns[-1], axis=1, inplace=True)
                    output_tables_list.append(snp_df.to_html(classes='snp_pairwiseMatrix', index=False))
                    titles_list.append('SNP pairwise Matrix')
                elif output_file == '{0}_genome_lengths.txt'.format(project):
                    genome_df = pd.read_table(os.path.join(results_dir, 'tables', output_file))
                    output_tables_list.append(genome_df.to_html(classes='genome_lengths', index=False))
                    titles_list.append('Genome Length')

        # Prepare tree files -- create symlinks between tree files in output directory and flask static directory
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        tree_file_list = [fname for fname in os.listdir(os.path.join(results_dir, 'trees')) if fname.endswith('.fasttree')]

        tree_files = []
        for tree in tree_file_list:
            tree_split = tree.split('/')[-1]
            target = os.path.join(target_dir, 'trees', tree_split)
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
                        tables=output_tables_list,
                        titles=titles_list, tree_files=tree_files, project=project)

    except Exception as e:
        logging.exception(str(e))
        return render_template('display.html',
                               tables=[],
                               titles=[], tree_files=[], project=project, file_links=[])




if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5090)
    # app.run(debug=True)
