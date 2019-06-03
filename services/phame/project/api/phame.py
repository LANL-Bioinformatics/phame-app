# services/phame/project/api/phame.py
import os
import requests
import zipfile
import shutil
import psutil
from tempfile import mkstemp
from time import ctime
from datetime import datetime
import stat
import logging
import json
import re
import pandas as pd
from uuid import uuid4
import celery.states as states
import ast
from sqlalchemy.exc import TimeoutError, IntegrityError, DataError
from flask import Blueprint, jsonify, request, render_template, redirect, \
    url_for, flash, send_file, current_app
from flask_login import current_user, login_required
from project.api.forms import InputForm, SubsetForm
from project.api.models import Project, User
from project.api.worker import celery
from project import db

phame_blueprint = Blueprint('phame', __name__, template_folder='templates',
                            static_folder='static')
# PROJECT_DIRECTORY = os.path.join('/phame_api', 'media')
# UPLOAD_DIRECTORY = os.path.join('static', 'uploads')
# PHAME_UPLOAD_DIR = os.path.join('/usr','src','app','static', 'uploads')

logging.basicConfig(filename='api.log', level=logging.DEBUG)


@phame_blueprint.route('/', methods=['GET'])
def index():
    specs = get_system_specs()
    return render_template('index.html', specs=specs)


def symlink_uploaded_file(dest_dir, upload_file, source_file=None):
    if not source_file:
        source_file = upload_file
    # logging.debug(f"upload file name {upload_file}")
    # logging.debug(f"dest_dir {dest_dir}")
    dest_file_path = os.path.join(dest_dir, upload_file)
    source_file_path = os.path.join(current_app.config['PHAME_UPLOAD_DIR'],
                                    current_user.username, source_file)
    if os.path.exists(dest_file_path):
        os.remove(dest_file_path)
    # logging.debug(f"file {source_file_path}")
    # logging.debug(f"symlink file {dest_file_path}")
    try:
        os.symlink(source_file_path, dest_file_path)

        # logging.debug(f"symlink exists {os.path.exists(dest_file_path)}")
    except FileNotFoundError as e:
        logging.debug(f'file {dest_file_path} not found: {e}')


def link_files(project_dir, ref_dir, work_dir, form):
    """
    Symlink files in user's upload directory in web container to project
    directory in PhaME container
    :param project_dir: Path to project directory
    :param ref_dir: Path to directory with reads and whole genome files
    :param work_dir: Path to directory with contigs and results files
    :param form: Input form
    :return:
    """
    # logging.debug(f"making links")
    os.makedirs(project_dir, exist_ok=True)

    if len(form.complete_genomes.data) > 0:
        if not os.path.exists(ref_dir):
            os.makedirs(ref_dir)
        # symlink complete genome files

        # logging.debug(f"ref_dir {ref_dir}")
        for upload_file in form.complete_genomes.data:
            # logging.debug(f"upload_file {upload_file}")
            symlink_uploaded_file(ref_dir, upload_file)
        form.reference_file.choices = \
            [(a, a) for a in form.complete_genomes.data]
    if len(form.reads.data) > 0:
        # symlink reads files
        for file_name in form.reads.data:
            # logging.debug(f"read {file_name}")
            symlink_uploaded_file(ref_dir, file_name)

    if len(form.contigs.data) > 0:
        os.makedirs(work_dir)
        # symlink contig files
        for file_name in form.contigs.data:
            # logging.debug(f"contig {file_name}")
            new_filename = os.path.splitext(file_name)[0] + '.contig'
            # logging.debug(f'contig file {new_filename}')
            symlink_uploaded_file(work_dir, new_filename,
                                  source_file=file_name)
    logging.debug(f"done making links")


def project_setup(form):
    """
    Checks if project exists and calls function to create symlinks
    :param form: Input form
    :return: project and reference directory paths
    """
    # logging.debug(f"project {form.project.data}")
    project_dir = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                               current_user.username, form.project.data)
    ref_dir = os.path.join(project_dir, 'refdir')
    work_dir = os.path.join(project_dir, 'workdir')
    # logging.debug(f'ref directory: {ref_dir}')
    # logging.debug(f'reference file: {form.reference_file.data}')
    # logging.debug(f'reference file: {form.project.data}')

    # logging.debug(os.path.exists(os.path.join(work_dir, 'results',
    #                                           f"{form.project.data}.log")))
    # project name for projects that have successfully completed must be unique
    if os.path.exists(os.path.join(work_dir,
                                   'results',
                                   f"{form.project.data}.log")
                      ) or (
            form.reference.data == 'Given' and len(
            form.reference_file.data) == 0):
        logging.debug(f"project {form.project.data} exists")
        return None, None
    logging.debug('done project setup')
    link_files(project_dir, ref_dir, work_dir, form)
    return project_dir, ref_dir


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
        logging.error('Could not remove directory {0}: {1}'.format(project_dir,
                                                                   str(e)))


def get_data_type(options_list):
    # determines what option to enter into config file based on which options
    # were selected in 'Data' from form
    # 0:only complete(F); 1:only contig(C); 2:only reads(R);
    # 3:combination F+C; 4:combination F+R; 5:combination C+R;
    # 6:combination F+C+R;
    if len(options_list) == 1:
        return options_list[0]
    else:
        return str(sum([int(x) + 1 for x in options_list]))


def create_config_file(form_dict):
    """
    create PhaME config.ctl file
    :param form_dict: dict with fields from InputForm
    :return:
    """
    # logging.debug(f'form dict {form_dict}')
    if 'csrf_token' in form_dict.keys():
        form_dict.pop('csrf_token')
    project = form_dict['project']

    form_dict['ref_dir'] = f'../{project}/refdir/'
    form_dict['work_dir'] = f'../{project}/workdir/'
    # logging.debug(f"threads {form_dict['threads']}")
    # if len(form.reference_file.data) > 0:
    #     form_dict['reference_file'] = form.reference_file.data
    form_dict['data_type'] = get_data_type(form_dict['data_type'])
    content = render_template('phame.tmpl', form=form_dict)
    # logging.debug(f'content {content}')

    with open(os.path.join(current_app.config['PROJECT_DIRECTORY'],
                           current_user.username,
                           project, 'config.ctl'), 'w') as conf:
        conf.write(content)


def bytes2human(n):
    # http://code.activestate.com/recipes/578019
    # >>> bytes2human(10000)
    # '9.8K'
    # >>> bytes2human(100001221)
    # '95.4M'
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n


def get_system_usage():
    mem = psutil.virtual_memory()
    mem_usage = (mem.total - mem.free - mem.buffers) / mem.total
    load = os.getloadavg()[1]
    cpu_usage = load / int(psutil.cpu_count) * 100
    fd = os.open(current_app.config['PROJECT_DIR'], os.O_RDONLY)
    fstat = os.fstatvfs(fd)
    disk_usage = fstat.f_frsize * fstat.f_bavail
    return mem_usage, cpu_usage, disk_usage


def get_system_specs():
    num_cpus = psutil.cpu_count()
    mem = psutil.virtual_memory()
    logging.debug(f'mem.total {mem.total}')
    total_ram = bytes2human(mem.total)
    return dict(num_cpus=num_cpus, total_ram=total_ram)


def get_log_mod_time(project):
    log_file = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                           current_user.username,
                           project, 'workdir', 'results', f'{project}.log')
    mod_time = os.path.getmtime(log_file)
    # logging.debug(f'mod_time {mod_time}')
    return datetime.utcfromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')


@phame_blueprint.route('/files', methods=['GET'])
def upload_files_list():
    file_list = os.listdir(os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                        current_user.username))
    return jsonify({'uploads': sorted(file_list)})


@phame_blueprint.route('/remove', methods=['POST'])
def remove_files():
    """Remove all of user's uploaded files"""
    file_list = os.listdir(os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                        current_user.username))
    for file_name in file_list:
        os.remove(os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                               current_user.username, file_name))
    file_list = os.listdir(os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                        current_user.username))
    return jsonify({'uploads': sorted(file_list)})


@phame_blueprint.route("/upload", methods=["POST"])
def upload():
    """Handle the upload of a file."""
    form = request.form

    # Create a unique "session ID" for this particular batch of uploads.
    upload_key = str(uuid4())
    # logging.debug(f'upload key {upload_key}')

    # Is the upload using Ajax, or a direct POST by the form?
    is_ajax = False
    if form.get("__ajax", None) == "true":
        is_ajax = True

    # Target folder for these uploads.
    target = os.path.join(current_app.config['PHAME_UPLOAD_DIR'],
                          current_user.username)
    # logging.debug(f'target directory {target}')
    if not os.path.exists(target):
        try:
            os.mkdir(target)
        except IOError:
            if is_ajax:
                return ajax_response(False,
                                     f"Couldn't create upload directory: "
                                     f"{target}")
            else:
                return "Couldn't create upload directory: {}".format(target)

    # logging.debug("=== Form Data ===")
    # for key, value in list(form.items()):
    #     logging.debug(key, "=>", value)

    # logging.debug(f'request files {request.files.getlist("file")}')
    for upload in request.files.getlist("file"):
        filename = os.path.basename(upload.filename)
        destination = "/".join([target, filename])
        # logging.debug(f"Accept incoming file: {filename}")
        # logging.debug("Save it to:", destination)
        upload.save(destination)

    if is_ajax:
        return ajax_response(True, upload_key)
    else:
        return redirect(url_for("phame.input"))


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
            project_statuses.append({'project': args_list[1],
                                     'state': status['state']})
    return project_statuses


def get_num_threads(project_dir):
    """
    Get the number of threads used for project run
    :param project_dir: Directory for project
    :return: number of threads
    """
    try:
        num_threads = get_config_property(project_dir, 'threads')
        if num_threads is None:
            num_threads = 'Unknown'
        return num_threads
    except IndexError as e:
        logging.debug(f'Could not get number of threads for {project_dir}')
        raise IndexError('IndexError')


def convert_seconds_to_time(exec_seconds):
    m, s = divmod(exec_seconds, 60)
    h, m = divmod(m, 60)
    exec_time_string = "%d:%02d:%02d" % (h, m, s)
    return exec_time_string


def get_exec_time(project_dir):
    """
    Get the project execution time from log file
    :param project_dir: Directory for project
    :return: project run time in seconds
    """
    exec_time = 0
    if os.path.exists(os.path.join(project_dir, 'time.log')):
        with open(os.path.join(project_dir, 'time.log'), 'r') as fp:
            exec_time = int(round(float(fp.readline()) / 1000.))

    return exec_time


def get_reference_file(summary_statistics_file):
    """
    Get the name of the reference genome file
    :param summary_statistics_file: Path to summary statistics file
    :return: Reference genome file name
    """
    if os.path.exists(summary_statistics_file) and os.path.getsize(
            summary_statistics_file) > 0:
        stats_df = pd.read_table(summary_statistics_file, header=None,
                                 index_col=0, squeeze=True)

        reference_genome = stats_df.loc['Reference used']
    else:
        logging.debug('no summary statistics file')
        reference_genome = ''

    return reference_genome


def set_project_status(project_statuses, project, reference_genome,
                       results_dir):
    """
    Set project status: if the status is available from the call to the
    monitor container, use that
    otherwise, see what results files are present
    :param project_statuses: list of dicts with project names and their states
    from get_project_statuses
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
        if not os.path.exists(
                os.path.join(results_dir,
                             f'{project}.log')) or reference_genome == '':
            project_task_status = 'FAILURE'
        else:
            project_task_status = 'SUCCESS'
    return project_task_status


def set_directories(display_user, project):
    """
    Set the directory names for the current project for the current user
    :param project: Project name
    :return: Full paths to project, work, results and reference directories
    """
    project_dir = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                               display_user, project)
    workdir = os.path.join(project_dir, 'workdir')
    results_dir = os.path.join(workdir, 'results')
    refdir = os.path.join(project_dir, 'refdir')
    return project_dir, workdir, results_dir, refdir


def fix_subset_tables(project, results_dir):
    """
    Copy the tables directory from original directory to subset project
    directory
    :param project: Name of project
    :param results_dir: Directory with results
    :return:
    """
    try:
        output_files_list = [f'{project}_summaryStatistics.txt',
                             f'{project}_coverage.txt',
                             f'{project}_snp_pairwiseMatrix.txt',
                             f'{project}_genome_lengths.txt']
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
        [fname for fname in os.listdir(refdir) if (
            fname.endswith('.fq') or fname.endswith('.fastq'))])

    contigs_file_count = len([fname for fname in os.listdir(workdir) if
                              fname.endswith('.contig')]) \
        if os.path.exists(workdir) else 0
    full_genome_file_count = len([fname for fname in os.listdir(refdir) if
                                  (fname.endswith('.fna') or fname.endswith(
                                      '.fasta'))])
    return reads_file_count, contigs_file_count, full_genome_file_count


def create_project_summary(project, project_status, num_threads,
                           reads_file_count, contigs_file_count,
                           full_genome_file_count, exec_time,
                           reference_genome):
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
    project_summary = \
        {'# of genomes analyzed':
            full_genome_file_count + contigs_file_count + reads_file_count,
         '# of contigs': contigs_file_count,
         '# of reads': reads_file_count,
         '# of full genomes': full_genome_file_count,
         'reference genome used': reference_genome,
         'project name': project,
         '# of threads': num_threads,
         'status': project_status,
         'execution time(h:m:s)': exec_time}
    logging.debug(f'project {project}')
    logging.debug(f'current user username {current_user.username}')
    if current_user.username != 'public':
        project_summary['delete'] = \
            f'<input name="deleteCheckBox" type="checkbox" ' \
            f'value={project} unchecked">'
    return project_summary


@phame_blueprint.route('/delete', methods=["POST"])
def delete_projects():
    """ Delete project directory files"""
    logging.debug('delete called')
    form = request.form
    projects = form.to_dict(flat=False)
    for project in projects['deleteCheckBox']:
        logging.debug(f'removing project: {project}')
        shutil.rmtree(os.path.join(current_app.config['PROJECT_DIRECTORY'],
                                   current_user.username, f'{project}'))
    return redirect(url_for('phame.projects'))


@phame_blueprint.route('/stats', methods=['POST'])
def add_stats():
    """
    Add project stats to database
    :param project:
    :return:
    """
    response_object = {
        'status': 'fail',
        'message': 'Invalid payload'
    }
    try:
        post_data = request.get_json()
        logging.debug(f'post_data {post_data}')
        project = post_data.get('project')
        status = post_data.get('status')
        logging.debug(f'project {project} status {status}')
        end_time = get_log_mod_time(project)
        logging.debug(f'end_time {end_time}')
        project_dir = os.path.join(current_app.config['PROJECT_DIRECTORY'], current_user.username, project)
        num_threads = get_num_threads(project_dir)
        exec_time = get_exec_time(project_dir)

        logging.debug(f'exec_time {exec_time}')
        user = User.query.filter_by(username=current_user.username).first()
        db.session.add(Project(name=project, end_time=end_time,
                               execution_time=exec_time,
                               num_threads=num_threads,
                               status=status, user=user))
        db.session.commit()
        response_object = {
            'status': 'success',
            'message': f'{project} status was added!'
        }
        return jsonify(response_object), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify(response_object), 400

@phame_blueprint.route('/stats/<project>', methods=['GET'])
def get_project_stats(project):
    """
    Get project stats
    :param project: project name
    :return: stats for project
    """
    response_object = {
        'status': 'fail',
        'message': 'Invalid payload'
    }
    try:
        user = User.query.filter_by(username=current_user.username).first()
        project_stats = Project.query.filter_by(name=project, user=user).first()

        response_object = {
            'status': 'success',
            'data': {
                'name': project_stats.name,
                'end_time': project_stats.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'num_threads': project_stats.num_threads,
                'execution_time':
                    project_stats.convert_seconds_to_time(),
                'status': project_stats.status
                }
        }
        return jsonify(response_object), 200
    except IntegrityError:
        db.session.rollback()
        return jsonify(response_object), 400


def get_all_project_stats():
    """
    Get project stats
    :return: stats for all projects
    """
    response_object = {
        'status': 'fail',
        'message': 'Invalid payload'
    }
    try:
        user = User.query.filter_by(username=current_user.username).first()

        return [project.to_json() for project in Project.query.filter_by(user=user)]
    except IntegrityError:
        db.session.rollback()
        return jsonify(response_object), 400


@phame_blueprint.route('/projects/<username>')
@phame_blueprint.route('/projects')
@login_required
def projects(username=None):
    """
    Displays run summaries and links to user's projects
    :return:
    """
    response_object = {'status': 'fail', 'message': 'Invalid payload'}
    try:
        pd.set_option('display.max_colwidth', 1000)

        display_user = \
            username if username and current_user.username == 'admin' else \
            current_user.username

        # logging.debug(f'display_user {display_user}')
        # list of all projects for this user
        if not os.path.exists(
                os.path.join(current_app.config['PROJECT_DIRECTORY'],
                             display_user)):
            os.makedirs(os.path.join(current_app.config['PROJECT_DIRECTORY'],
                                     display_user))
        # projects_list = [project for project in
        #                  os.listdir(os.path.join(
        #                      current_app.config['PROJECT_DIRECTORY'],
        #                      display_user))]
        projects_list = get_all_project_stats()
        logging.debug(f"projects project_stats {projects_list}")
        # proj_list = project_stats
        # logging.debug(f'projects proj_list {proj_list}')
        user = User.query.filter_by(username=current_user.username).first()
        response_object = {'status': 'success', 'data': {
            'projects': projects_list}}
    #     return jsonify(response_object), 200
    # except IntegrityError:
    #     db.session.rollback()
    #     return jsonify(response_object), 400

        if len(projects_list) == 0 and current_user.username != 'public':
            return redirect(url_for('phame.input'))
        if len(projects_list) == 0 and current_user.username == 'public':
            return redirect(url_for('phame.index'))

        # projects_list.sort()

        # list of projects to display
        projects_display_list = []

        project_statuses = get_project_statuses(display_user)

        for project in projects_list:

            logging.debug(f'{project}')

            project_dir, workdir, results_dir, refdir = \
                set_directories(display_user, project['name'])

            # hack to fix tables for subsetted projects
            if re.search('_subset$', project['name']):
                fix_subset_tables(project['name'], results_dir)

            summary_statistics_file = \
                os.path.join(results_dir, 'tables',
                             f"{project['name']}_summaryStatistics.txt")

            # create output tables
            reads_file_count, contigs_file_count, full_genome_file_count = \
                get_file_counts(refdir, workdir)

            num_threads = get_num_threads(project_dir)

            exec_time_secs = get_exec_time(project_dir)
            exec_time = convert_seconds_to_time(exec_time_secs)

            reference_genome = get_reference_file(summary_statistics_file)

            project_task_status = set_project_status(project_statuses,
                                                     project['name'],
                                                     reference_genome,
                                                     results_dir)

            project_summary = create_project_summary(project['name'],
                                                     project_task_status,
                                                     num_threads,
                                                     reads_file_count,
                                                     contigs_file_count,
                                                     full_genome_file_count,
                                                     exec_time,
                                                     reference_genome)
            projects_display_list.append(project_summary)

        run_summary_df = pd.DataFrame(projects_display_list)

        # add delete project checkbox if user is not public
        if current_user.username != 'public':
            run_summary_columns = \
                ['project name', '# of genomes analyzed',
                 '# of contigs', '# of reads',
                 'reference genome used', '# of threads',
                 'status', 'execution time(h:m:s)', 'delete']
        else:
            run_summary_columns = ['project name', '# of genomes analyzed',
                                   '# of contigs', '# of reads',
                                   'reference genome used', '# of threads',
                                   'status', 'execution time(h:m:s)']

        # Turn project name into a link to the display page if it's finished
        # running successfully
        run_summary_df['project name'] = \
            run_summary_df[['project name', 'status']].apply(
            lambda x: '<a href="/phame/display/{0}/{1}">{1}</a>'.format(
                display_user, x['project name']) if (x['status'] == 'SUCCESS')
            else x['project name'], axis=1)

        run_summary_df = run_summary_df[run_summary_columns]

        return render_template('projects.html',
                               run_summary=run_summary_df.to_html(
                                   escape=False, classes='run summary',
                                   index=False))
    except Exception as e:
        logging.exception(str(e))
        return render_template('error.html',
                               error={
                                   'msg': f'There was a problem displaying '
                                   f'projects: {str(e)}'})


@phame_blueprint.route('/input', methods=['GET', 'POST'])
@login_required
def input():
    """
    Takes flask form, checks parameters to make sure they are correct for
    PhaME, creates PhaME config
    file
    :return:
    """
    if current_user.username == 'public':
        return redirect(url_for('phame.projects'))

    form = InputForm()
    if not os.path.exists(os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                       current_user.username)):
        os.makedirs(os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                 current_user.username))
    files_list = sorted(os.listdir(os.path.join(
        current_app.config['UPLOAD_DIRECTORY'], current_user.username)))
    form.reference_file.choices = []
    form.complete_genomes.choices = [
        (a, a) for a in files_list if (
            a.endswith('fna') or a.endswith('fasta') or a.endswith('gff'))]
    form.contigs.choices = [
        (a, a) for a in files_list if a.endswith('contig')]
    form.reads.choices = [(a, a) for a in files_list if a.endswith('fastq')]

    if request.method == 'POST':
        # logging.debug(f'request method {request.method}')
        # logging.debug(f'reference file {form.reference_file.data}')
        if len(form.project.data) == 0:
            error = 'Please enter a project name'
            return render_template('input.html', title='Phame input',
                                   form=form, error=error)
        # logging.debug(f'form {request.form}')
        # logging.debug(f'form flat {request.form.to_dict(flat=False)}')
        # logging.debug(f'form {request.form.to_dict()}')
        project_dir, ref_dir = project_setup(form)
        # logging.debug(f'ref file {form.reference_file.data}')
        if project_dir is None:
            # project creation failed because there is an existing project
            # that successfully completed
            error = 'Project directory already exists'
            return render_template('input.html', title='Phame input',
                                   form=form, error=error)
        if form.validate_on_submit():
            # logging.debug(f"data {form.data_type.data}")

            # Perform validation based on requirements of PhaME
            if (
                '1' in form.data_type.data or '2' in form.data_type.data
            ) and len(form.reference_file.data) == 0:
                error = 'You must upload a reference genome if you select ' \
                        'Contigs or Reads from Data'
                remove_uploaded_files(project_dir)
                return render_template('input.html', title='Phame input',
                                       form=form, error=error)

            # Ensure each fasta file has a corresponding mapping file if
            # Generate SNPs is yes and 'random' or 'ani'
            if form.cds_snps.data == '1' and (
                    form.reference.data == '0' or form.reference.data == '2'):
                for fname in os.listdir(ref_dir):
                    if fname.endswith(
                            '.fa') or fname.endswith(
                            '.fasta') or fname.endswith('.fna'):
                        if not os.path.exists(os.path.join(
                            ref_dir, f"{fname.split('.')[0]}.{'gff'}")
                        ):
                            remove_uploaded_files(project_dir)
                            error = \
                                'Each full genome file must have a ' \
                                'corresponding .gff file if "Generate SNPs ' \
                                'from coding regions" ' \
                                'is yes and "Reference" is random or ANI'
                            return render_template('input.html',
                                                   title='Phame input',
                                                   form=form, error=error)

            # Ensure a reference file is selected if the Reference option
            # selected is 'manual selection'
            if form.reference.data == '1' and len(
                    form.reference_file.data) == 0:
                error = 'You must select a reference genome if you select ' \
                        '"manual selection" from the Reference menu'
                remove_uploaded_files(project_dir)
                return render_template('input.html', title='Phame input',
                                       form=form, error=error)
            # Create config file
            create_config_file(request.form.to_dict())

            return redirect(url_for('phame.runphame',
                                    project=form.project.data))

    return render_template('input.html', title='Phame input', form=form)


def get_config_property(project_dir, config_property):
    value = None
    try:
        config_df = pd.read_csv(os.path.join(project_dir, 'config.ctl'),
                                sep='=', header=None, names=['field', 'val'])
        config_df = config_df.loc[pd.notna(config_df['val']), :]
        config_df['field'] = config_df['field'].apply(lambda x: x.strip())
        # logging.debug(f'config_property {config_property}')
        # logging.debug(f"config_field {config_df[config_df['field'] == config_property]['val']}")
        value = config_df[config_df['field'] == config_property]['val'].values[0].strip().split('#')[0].strip()
    except IOError as e:
        logging.exception(f'Cannot get config property {config_property} for project '
                          f'directory {project_dir}: {e}')
    except IndexError as e:
        logging.debug(f'IndexError Cannot get config property {config_property} for project ' 
                      f'directory {project_dir}: {e}')
    return value


@phame_blueprint.route('/subset/<project>', methods=['GET', 'POST'])
@login_required
def subset(project):
    form = SubsetForm()
    project_path = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                                current_user.username, project)
    new_project = project + '_subset'
    new_project_path = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                                    current_user.username, new_project)

    ref_dir_files = sorted(os.listdir(os.path.join(project_path, 'refdir')))

    form.subset_files.choices = [(a, a) for a in ref_dir_files if
                                 (a.endswith('fna') or a.endswith('fasta'))]

    if request.method == 'POST':
        # logging.debug('POST')
        # logging.debug('post subset files: {0}'.format(form.subset_files.data))

        # Delete subset directory tree and create new directories
        if os.path.exists(new_project_path):
            shutil.rmtree(new_project_path)
        os.makedirs(os.path.join(new_project_path, 'refdir'))
        os.makedirs(os.path.join(new_project_path, 'workdir'))

        # Change project name in config file
        shutil.copy(os.path.join(project_path, 'config.ctl'),
                    os.path.join(new_project_path))

        # copy selected results directories to new project
        dir_list = ['gaps', 'miscs', 'snps', 'stats', 'temp', 'trees',
                    'tables']
        for results_dir in dir_list:
            shutil.copytree(os.path.join(project_path, 'workdir', 'results',
                                         results_dir),
                            os.path.join(new_project_path, 'workdir',
                                         'results', results_dir))

        # copy files from results directory
        results_files = os.listdir(os.path.join(project_path, 'workdir',
                                                'results'))
        for result_file in results_files:
            if not os.path.isdir(os.path.join(project_path, 'workdir',
                                              'results', result_file)):
                # logging.debug(f'result file {result_file}')
                # logging.debug(f'isdir {os.path.isdir(result_file)}')
                shutil.copy(os.path.join(project_path, 'workdir', 'results',
                                         result_file),
                            os.path.join(new_project_path, 'workdir',
                                         'results'))

        # create new working_list.txt file and copy files
        if not os.path.exists(os.path.join(new_project_path, 'workdir',
                                           'files')):
            os.mkdir(os.path.join(new_project_path, 'workdir', 'files'))
        with open(os.path.join(new_project_path, 'workdir',
                               'working_list.txt'), 'w') as fp:
            for ref_file in form.subset_files.data:
                fp.write(f'{os.path.splitext(ref_file)[0]}\n')
                if ref_file.endswith('fasta'):
                    ref_file = os.path.splitext(ref_file)[0] + '.fna'
                if os.path.exists(os.path.join(project_path, 'workdir',
                                               'files', ref_file)):
                    shutil.copy(os.path.join(project_path, 'workdir', 'files',
                                             ref_file),
                                os.path.join(new_project_path, 'workdir',
                                             'files', ref_file))

        # modify config.ctl file to change project to new name and get
        # reference file name
        fh, abs_path = mkstemp()
        with os.fdopen(fh, 'w') \
                as tmp, open(os.path.join(new_project_path,
                                          'config.ctl'), 'r') as config:
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
                    reference_file = line.split('=')[1].split()[0]
                    # logging.debug('reference line {0}'.format(line))
        shutil.move(abs_path, os.path.join(new_project_path, 'config.ctl'))

        # symlink subset of reference genome files
        for file_name in form.subset_files.data:

            # logging.debug(f'file {file_name}')
            os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'],
                                    current_user.username, file_name),
                       os.path.join(new_project_path, 'refdir', file_name))

        # symlink contig files
        for file_name in os.listdir(os.path.join(project_path, 'workdir')):
            if file_name.endswith('.contig'):
                os.symlink(os.path.join(
                    current_app.config['PHAME_UPLOAD_DIR'],
                    current_user.username, file_name),
                    os.path.join(new_project_path, 'workdir', file_name))

        if form.validate_on_submit():
            if reference_file not in form.subset_files.data:
                flash(f'Please include the reference file {reference_file}')
                return redirect(url_for('subset', project=project))

            return redirect(url_for('phame.runphame', project=new_project))

    return render_template('subset_input.html', title='Subset Phame input',
                           form=form)


@phame_blueprint.route('/download/<project>')
def download(project):
    """
    Calls function to zip project output files and downloads the zipfile when
    link is clicked
    :param project:
    :return:
    """
    zip_name = zip_output_files(project)
    return send_file(zip_name, mimetype='zip', attachment_filename=zip_name,
                     as_attachment=True)


def zip_output_files(project):
    """
    Create a zip file of all files in user's results directory
    :param project: name of project
    :return: zip_name: name of zip file
    """
    zip_name = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                            current_user.username, project, f'{project}.zip')
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in \
            os.walk(os.path.join(current_app.config['PROJECT_DIRECTORY'],
                                 current_user.username, project, 'workdir',
                                 'results')):
            for file in files:
                zipf.write(os.path.join(root,
                                        file), os.path.relpath(
                    os.path.join(root, file),
                    os.path.join(current_app.config['PROJECT_DIRECTORY'],
                                 current_user.username, project, '..')))
    return zip_name


@phame_blueprint.route('/check/<string:task_id>')
def check_task(task_id):
    """
    Endpoint for api that checks task status
    :param task_id: Celery task id
    :return: json of task state
    """
    res = celery.AsyncResult(task_id)
    # logging.debug('res state' + res.state)
    if res.state == states.PENDING or res.state == 'PROGRESS':
        result = res.state
    else:

        result = str(res.result)
    # logging.debug('result ' + str(result))
    if str(result) is None:
        # logging.debug('result is None')
        return render_template(
            'error.html',
            error={'msg': 'Task status could not be obtained'})
    return jsonify({'Result': result, 'task_output': json.dumps(res.result)})


@phame_blueprint.route('/wait/<string:task_id>/<project>',
                       methods=['POST', 'GET'])
def wait(task_id, project):
    """
    Creates wait page that displays task status while project is executing
    :param task_id: Celery task id
    :param project: Project name
    :return:
    """
    try:
        return render_template(
            'wait.html',
            status_url=url_for('phame.check_task', task_id=task_id),
            project=project, username=current_user.username)
    except TimeoutError as e:
        return render_template('error.html', error={'msg': str(e)})


@phame_blueprint.route('/runphame/<project>', methods=['POST', 'GET'])
def runphame(project):
    """
    Creates celery task to run PhaME
    :param project: Project name
    :return:
    """
    task = celery.send_task('tasks.run_phame',
                            args=[current_user.username, project])
    logging.debug('task id: {0}'.format(task.id))
    response = check_task(task.id)
    if isinstance(response, dict):
        logging.debug(f'check task {response.__dict__}')
    return redirect(url_for('phame.wait', task_id=task.id, project=project))


@phame_blueprint.route('/get_log/<project>', methods=['GET'])
def get_log(project):
    """
    Endpoint for api call to get project log
    :param project: Project name
    :return: json of log file
    """
    log_file = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                            current_user.username, project, 'workdir',
                            'results', f'{project}.log')
    if not os.path.exists(log_file):
        return jsonify({'log': 'null'})
    with open(log_file, 'rb') as f:
        f.seek(-2, os.SEEK_END)  # Jump to the second last byte.
        while f.read(1) != b"\n":  # Until EOL is found...
            f.seek(-2, os.SEEK_CUR)  # ...jump back the read byte plus one more
        last = f.readline()
    return jsonify({'log': str(last)})


@phame_blueprint.route('/num_results_files/<project>', methods=['GET'])
def num_results_files(project):
    results_dir = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                               current_user.username, project, 'workdir',
                               'results')
    num_files = len(os.listdir(results_dir)) \
        if os.path.exists(results_dir) else 0
    return jsonify({'num_files': num_files})


def send_mailgun(message, project):
    key = os.environ['MAILGUN_KEY']
    email_domain = 'mail.edgebioinformatics.org'
    recipient = current_user.email
    # logging.info('current_user.email: {0}'.format(recipient))
    request_url = f'https://api.mailgun.net/v3/{email_domain}/messages'
    results_dir = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                               current_user.username, project, 'workdir',
                               'results')
    log_file = '{0}.log'.format(project)
    log_fh = open(os.path.join(results_dir, log_file), "rb").read()
    error_file = f'{project}.error'
    error_fh = open(os.path.join(results_dir, error_file), "rb").read()
    mail_request = requests.post(
        request_url,
        auth=('api', key),
        files=[("attachment", log_fh), ("attachment", error_fh)],
        data={'from': 'donotreply@edgebioinformatics.org', 'to': recipient,
              'subject': f'Project {project}', 'text': message})
    # logging.debug(f"from: {'donotreply@edgebioinformatics.org'} to: "
    #               f"{recipient} subject: Project {project} text: {message}")
    # logging.debug(f'log file: {log_file}, error file: {error_file}')
    # logging.info('Status: {0}'.format(mail_request.status_code))
    return mail_request.status_code


@phame_blueprint.route('/notify/<project>', methods=['GET'])
def notify(project):
    # logging.debug(f"send notifications: {app.config['SEND_NOTIFICATIONS']}")
    if current_app.config['SEND_NOTIFICATIONS']:
        try:
            state = \
                send_mailgun(f'Your project {project} has finished running',
                             project)
            logging.info(f'message sent to {current_user.email} for project '
                         f'{project} status code {state}')
        except os.error as e:
            logging.error(str(e))
    return redirect(url_for('phame.display', username=current_user.username,
                            project=project))


@phame_blueprint.route('/display/<project>', methods=['POST', 'GET'])
@phame_blueprint.route('/display/<username>/<project>',
                       methods=['POST', 'GET'])
def display(project, username=None):
    """
    Displays output from PhaME, including summary statistics, sequence lengths
    and tree output using archeopteryx.js library
    Creates a symlink between PhaME output tree file and static directory in
    flask directory
    :param project: project name
    :param username: optional username of user
    :return: renders PhaME output page
    """

    if not username:
        username = current_user.username
    project_dir = os.path.join(current_app.config['PROJECT_DIRECTORY'],
                               username, project)
    workdir = os.path.join(project_dir, 'workdir')
    results_dir = os.path.join(workdir, 'results')
    refdir = os.path.join(project_dir, 'refdir')
    trees_target_dir = os.path.join(os.path.dirname(__file__), 'static',
                                    'trees', username)

    if not os.path.exists(workdir):
        error = {'msg': 'Directory does not exist {0}'.format(workdir)}
        return render_template('error.html', error=error)

    # create output tables
    reads_count = len(
        [fname for fname in os.listdir(refdir) if
         (fname.endswith('.fq') or fname.endswith('.fastq'))])
    contigs_count = len(
        [fname for fname in os.listdir(workdir) if fname.endswith('.contig')])
    full_genome_count = len(
        [fname for fname in os.listdir(refdir) if (
            fname.endswith('.fna') or fname.endswith('.fasta'))])
    # logging.debug(f'# reads files {reads_count}, '
    #               f'# contig files {contigs_count}, '
    #               f'# full genomes {full_genome_count}, '
    #               f'len(length_df) {full_genome_count*3-1}')

    output_files_list = [f'{project}_summaryStatistics.txt',
                         f'{project}_coverage.txt',
                         f'{project}_snp_pairwiseMatrix.txt',
                         f'{project}_genome_lengths.txt']

    output_tables_list = []
    titles_list = []
    num_genomes = reads_count + contigs_count + full_genome_count
    try:
        for output_file in output_files_list:
            if os.path.exists(os.path.join(results_dir, 'tables',
                                           output_file)):
                if output_file == f'{project}_summaryStatistics.txt':
                    # run_time = '' if not log_time else log_time[:6]
                    stats_df = pd.read_table(os.path.join(results_dir,
                                                          'tables',
                                                          output_file),
                                             header=None, index_col=0)
                    del stats_df.index.name
                    stats_df.columns = ['']

                    run_summary_df = pd.DataFrame(
                        {'# of genomes analyzed': num_genomes,
                         '# of contigs': contigs_count,
                         '# of reads': reads_count,
                         '# of full genomes': full_genome_count,
                         'reference genome used':
                             stats_df.loc['Reference used'],
                         'project name': project})
                    output_tables_list.append(run_summary_df.to_html(
                        classes='run_summary'))
                    output_tables_list.append(
                        stats_df.to_html(classes='stats'))
                    titles_list.append('Run Summary')
                    titles_list.append('Summary Statistics')
                elif output_file == f'{project}_coverage.txt':
                    coverage_df = pd.read_table(os.path.join(results_dir,
                                                             'tables',
                                                             output_file))
                    output_tables_list.append(
                        coverage_df.to_html(classes='coverage'))
                    titles_list.append('Genome Coverage')
                elif output_file == f'{project}_snp_pairwiseMatrix.txt':
                    snp_df = pd.read_table(os.path.join(results_dir, 'tables',
                                                        output_file), sep='\t')
                    snp_df.rename(index=str, columns={'Unnamed: 0': 'Genome'},
                                  inplace=True)
                    snp_df.drop(snp_df.columns[-1], axis=1, inplace=True)
                    snp_df.set_index('Genome', inplace=True)
                    snp_df = \
                        snp_df[list(snp_df.columns)].fillna(0.0).astype(int)
                    output_tables_list.append(
                        snp_df.to_html(classes='snp_pairwiseMatrix',
                                       index=True))
                    titles_list.append('SNP pairwise Matrix')
                elif output_file == f'{project}_genome_lengths.txt':
                    genome_df = pd.read_table(os.path.join(results_dir,
                                                           'tables',
                                                           output_file))
                    output_tables_list.append(
                        genome_df.to_html(classes='genome_lengths',
                                          index=False))
                    titles_list.append('Genome Length')

        # Prepare tree files -- create symlinks between tree files in output
        # directory and flask static directory
        if not os.path.exists(trees_target_dir):
            os.makedirs(trees_target_dir)
        # logging.debug(f'tree directory:{trees_target_dir}')
        tree_file_list = [
            fname for fname in os.listdir(os.path.join(results_dir, 'trees'))
            if fname.endswith(
                '.fasttree') or fname.endswith(
                '.treefile'
            ) or 'bestTree' in fname or 'bipartitions' in fname]

        tree_files = []
        for tree in tree_file_list:
            tree_split = tree.split('/')[-1]
            target = os.path.join(trees_target_dir, tree_split)
            tree_files.append(tree_split)
            # logging.debug('fasttree file: trees/{0}'.format(tree_split))
            source = os.path.join(results_dir, 'trees', tree_split)
            if not os.path.exists(target):
                os.symlink(source, target)
            if not os.path.exists(target):
                error = {'msg': 'File does not exists {0}'.format(target)}
                return render_template('error.html', error=error)

        # logging.debug(f'results dir: {results_dir}/trees/*.fastree')

        return render_template('display.html',
                               username=username,
                               tables=output_tables_list,
                               titles=titles_list, tree_files=tree_files,
                               project=project)

    except Exception as e:
        logging.exception(str(e))
        return render_template('display.html',
                               tables=[],
                               titles=[], tree_files=[], project=project,
                               file_links=[])


@phame_blueprint.route('/display_tree/<username>/<project>/<tree>')
def display_tree(username, project, tree):
    """
    Creates phylogeny tree using archeopteryx.js
    :param username: user's name
    :param project: Name of project
    :param tree: Name of tree file (.fasttree)
    :return:
    """
    return render_template('tree_output.html', username=username, tree=tree,
                           project=project)


@phame_blueprint.route('/display_file/<project>/<filename>')
def display_file(filename, project):
    """
    Create page to display text file
    :param filename: Name of file to display
    :param project: Project name
    :return:
    """
    with open(os.path.join(current_app.config['PROJECT_DIRECTORY'],
                           current_user.username, project,
                           'workdir', 'results', filename),
              'r') as fp:
        content = fp.read()
    return render_template('content.html', text=content)
