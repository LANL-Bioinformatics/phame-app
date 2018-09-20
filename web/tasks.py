import os
import time
from celery import Celery
import subprocess
from celery.utils.log import get_task_logger
from json import dumps

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

logger = get_task_logger(__name__)

@celery.task(name='tasks.run_phame', bind=True)
def phame_run(self, project, username):
    try:
        logger.info('run_phame called with {0}/{1}'.format(project, username))
        cmd = ['./docker_run_phame.sh', '{0}/{1}'.format(project, username) ]
        p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info('process launched')
        stdout, stderr = p1.communicate()
        logger.debug(stdout)
        logger.debug(stderr)
    except subprocess.CalledProcessError as e:
        logger.error(str(e))
        return dumps({'error': str(e)})
    except celery.exceptions.TaskError as e:
        logger.error(str(e))

    return stdout
