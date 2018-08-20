import os
import time
from celery import Celery
import requests
import logging
import subprocess

logging.basicConfig(filename='phame_tasks.log', level=logging.DEBUG)

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


@celery.task(name='tasks.add')
def add(x, y):
    time.sleep(5)
    return x + y

#
# @celery.task(name='tasks.run_phame')
# def run_phame(project, username):
#     r = requests.post('http://phame:5001/runphame/{0}/{1}'.format(username, project))
#     return r.text


@celery.task(name='tasks.run_phame', bind=True)
def phame_run(self, project, username):
    logging.debug(self.request.id)
    logging.debug('run_phame called with {0}'.format(project, username))
    try:

        p1 = subprocess.Popen('./docker_run_phame.sh {0}/{1}'.format(project, username), shell=True,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p1.communicate()
        logging.debug(stdout)
        logging.debug(stderr)
    except subprocess.CalledProcessError as e:
        logging.error(str(e))
        # error = str(e)
        return "An error occurred while trying to run PhaME: {0}".format(str(e))
    return stdout
