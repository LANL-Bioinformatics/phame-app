from flask import Flask
from flask import render_template, redirect
import subprocess
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Flask Dockerized'

@app.route('/run')
def run_phame():
    try:
        p1 = subprocess.Popen('./docker_run_phame.sh', shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p1.communicate()

    except subprocess.CalledProcessError as e:
        return "An error occurred while trying to run PhaME: {0}".format(str(e))

    return redirect('/display')

@app.route('/index')
def index():
    user = {'username': 'Mark'}
    return render_template('index.html', title='Home', user=user)


@app.route('/display', methods=['POST', 'GET'])
def display():
    return render_template('archeo_example.html')

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
