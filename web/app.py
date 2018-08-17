import os
import zipfile
import shutil
import datetime
import glob
import time
from flask import Flask, render_template, redirect, flash, url_for, request, send_file, jsonify

from werkzeug.utils import secure_filename
from werkzeug.urls import url_parse
import subprocess
import logging

app = Flask(__name__)

logging.basicConfig(filename='phame.log', level=logging.DEBUG)



@app.route('/runphame/<project>/<username>', methods=['POST', 'GET'])
def runphame(project, username):
    try:
        logging.debug('run_phame called with {0}'.format(project, username))
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

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5001)
