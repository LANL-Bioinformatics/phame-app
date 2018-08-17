import os
import time
from celery import Celery
import subprocess
import time
# from phame_api01.api import app
import logging


CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)
basedir = os.path.dirname(os.path.dirname(__file__))

logging.basicConfig(filename='tasks.log', level=logging.DEBUG)
logging.debug(os.path.join(basedir, 'phame_api01', 'media'))

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        name = kw.get('log_name', method.__name__.upper())
        kw['log_time'][name] = te-ts

        return result
    return timed


@celery.task(name='tasks.add')
def add(x, y):
    logging.debug('tasks.add called')
    time.sleep(5)
    return x + y


@celery.task(name='tasks.run_phame')
def run_phame(project, username, **kwargs):
    """
    Calls shell script that runs PhaME
    :param project: name of project
    :return: redirects to display view
    """
    error = None
    try:
        logging.debug('run_phame called!!!!!!!!!!!!!!')
        p1 = subprocess.Popen('./docker_run_phame.sh {0}/{1}'.format(username, project), shell=True,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)



        stdout, stderr = p1.communicate()
        logging.debug(stdout)
        logging.error(stderr)
        if len(stderr) > 0 or os.path.exists(os.path.join(app.config['PROJECT_DIRECTORY'], username, project, 'workdir', 'results', '{0}.error'.format(project))):
            # logging.error(stderr)
            # logging.error('current user: {0}, project: {1}'.format(username, project))
            error = {'msg':stderr}

            # return redirect(url_for('error', error=error))

    except subprocess.CalledProcessError as e:
        logging.error(str(e))
        # error = str(e)
        return "An error occurred while trying to run PhaME: {0}".format(str(e))

    return stdout
