import os
import time
from celery import Celery
import subprocess
from subprocess import PIPE
from celery.utils.log import get_task_logger
from json import dumps

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

logger = get_task_logger(__name__)


def log_subprocess_output(pipe):
    for line in iter(pipe.readline, b''): # b'\n'-separated lines
        logger.info('got line from subprocess: %r', line)


@celery.task(name='tasks.run_phame', bind=True)
def phame_run(self, project, username):
    try:
        logger.info("run_phame called '/usr/local/bin/runPhaME /phame_api/media/{0}/{1}/config.ctl".format(project, username))
        cmd = ['./docker_run_phame.sh', '{0}/{1}'.format(project, username) ]
        # p1 = subprocess.Popen('./docker_run_phame.sh {0}/{1}'.format(project, username), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p1 = subprocess.Popen(['/usr/local/bin/runPhaME /phame_api/media/{0}/{1}/config.ctl'.format(project, username)], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        logger.info('process launched')
        with p1.stdout:
            log_subprocess_output(p1.stdout)
        # exitcode = p1.wait()
        # stdout, stderr = p1.communicate()
        # logger.debug(stdout)
        # logger.debug(stderr)
    except subprocess.CalledProcessError as e:
        logger.error(str(e))
        return dumps({'error': str(e)})
    except celery.exceptions.TaskError as e:
        logger.error(str(e))

    return p1.stdout
