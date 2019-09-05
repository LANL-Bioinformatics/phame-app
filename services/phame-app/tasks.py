import os
import time
from celery import Celery
import subprocess
from subprocess import PIPE
from celery.utils.log import get_task_logger
from json import dumps
import time
import zipfile

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

logger = get_task_logger(__name__)


def log_subprocess_output(pipe):
    try:
        for line in iter(pipe.readline, b''): # b'\n'-separated lines
            logger.info('subprocess output: %r', line)
        logger.info('Done writing output')
    except Exception as e:
        logger.error('Error writing output {0}'.format(str(e)))


@celery.task(name='tasks.run_phame', bind=True)
def phame_run(self, project, output_directory):
    try:
        start_time = int(round(time.time() * 1000))
        logger.info(f"run_phame called '/usr/local/bin/phame {output_directory}/config.ctl")
        cmd = ['phame', f'{output_directory}/config.ctl']
        p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        logger.info('process launched')
        try:
            with p1.stdout:
                for line in p1.stdout:
                    self.update_state(state='PROGRESS', meta={'status':str(line)})
                    logger.info('subprocess output: %r', line)
        except Exception as e:
            logger.error(str(e))
        log_time = int(round(time.time() * 1000)) - start_time
        logger.info('Exited writing output')
        # logger.info(f'time {log_time}')
        with open(f"{output_directory}/time.log", 'w') as fp:
            fp.write(str(log_time))
        zip_name = zip_output_files(project, output_directory)
        logger.info(f'zipped {zip_name}')
    except subprocess.CalledProcessError as e:
        logger.error(str(e))
        return dumps({'error': str(e)})
    except celery.exceptions.TaskError as e:
        logger.error(str(e))


def zip_output_files(project_name, output_directory):
    """
    Create a zip file of all files in user's results directory
    :param project_name: name of project
    :return: output_directory: directory with output files
    """
    zip_name = os.path.join(output_directory, f'{project_name}.zip')
    logger.info(f'zip output directory {output_directory}')
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in \
            os.walk(os.path.join(output_directory, 'workdir',
                                 'results')):
            for file in files:
                file_path = os.path.join(root, file)
                logger.info(f'zipping {file_path}')
                logger.info(f"zipping to {os.path.relpath(file_path,os.path.join(output_directory, '..'))}")
                zipf.write(file_path, os.path.relpath(
                    file_path,
                    os.path.join(output_directory, '..')))
    return zip_name
