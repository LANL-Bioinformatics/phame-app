import os
import time
from celery import Celery
import subprocess
from subprocess import PIPE
from celery.utils.log import get_task_logger
from json import dumps
import time

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

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
def phame_run(self, project, username):
    try:
        start_time = int(round(time.time() * 1000))
        logger.info("run_phame called '/usr/local/bin/phame /phame_api/media/{0}/{1}/config.ctl".format(project, username))
        cmd = ['phame', '/phame_api/media/{0}/{1}/config.ctl'.format(project, username)]
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
        with open("/phame_api/media/{0}/{1}/time.log".format(project, username), 'w') as fp:
            fp.write(str(log_time))

    except subprocess.CalledProcessError as e:
        logger.error(str(e))
        return dumps({'error': str(e)})
    except celery.exceptions.TaskError as e:
        logger.error(str(e))

