from flask import Flask
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
        # with open('stdout.txt', 'w') as fp:
        #     fp.write(str(stderr))
        #     fp.write('\n')
        #     fp.write(str(stdout))
        # print(stderr)
        # print(stdout)
    except subprocess.CalledProcessError as e:
        return "An error occurred while trying to run PhaME: {0}".format(str(e))
    return 'Finished docker_run_phame {0}'.format(str(stdout))

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
