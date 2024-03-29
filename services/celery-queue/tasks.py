import os
import time
from celery import Celery
import requests
import logging
import subprocess
logging.basicConfig(filename='phame.log', level=logging.DEBUG)

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


@celery.task(name='tasks.add')
def add(x, y):
    time.sleep(5)
    return x + y


@celery.task(name='tasks.run_phame')
def run_phame(project, username):
    r = requests.post('http://phame:5001/runphame/{0}/{1}'.format(username, project))
    return r.text
