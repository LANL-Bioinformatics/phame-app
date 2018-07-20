import os
from flask import Flask, render_template, redirect, flash, url_for, request, render_template_string
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
import subprocess
from forms import LoginForm, InputForm
from config import Config
app = Flask(__name__)
app.config.from_object(Config)

def upload_files(request, form):
    if form.reference_file.data:
        reference_file = request.files['reference_file']
        filename = secure_filename(reference_file.filename)
        reference_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    if form.ref_dir.data:
        for file_name in request.files.getlist("ref_dir"):
            filename = secure_filename(file_name.filename)
            file_name.save(os.path.join(app.config['UPLOAD_FOLDER'], 'refdir',  filename))

    if form.work_dir.data:
        for file_name in request.files.getlist("work_dir"):
            filename = secure_filename(file_name.filename)
            file_name.save(os.path.join(app.config['UPLOAD_FOLDER'], 'workdir',  filename))


@app.route('/run/<project>')
def run_phame(project):
    try:
        p1 = subprocess.Popen('./docker_run_phame.sh', shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p1.communicate()

    except subprocess.CalledProcessError as e:
        return "An error occurred while trying to run PhaME: {0}".format(str(e))

    return redirect(url_for('display', tree_file ='{0}_all.fasttree'.format(project)))

@app.route('/')
@app.route('/index')
def index():
    user = {'username': 'Mark'}
    return render_template('index.html', title='Home', user=user)


@app.route('/display/<tree_file>', methods=['POST', 'GET'])
def display(tree_file):
    source = os.path.join('/phame_api01/phame_api01/media/workdir/results/', tree_file)
    target = os.path.join('static', tree_file)
    if not os.path.exists(target):
        os.symlink(source, target)
    return render_template('tree_output.html', tree= tree_file)


@app.route('/input', methods=['GET', 'POST'])
def input():
    form = InputForm()
    if request.method == 'POST':
        if 'reference_file' not in request.files:
            flash('No reference file')
            return redirect(request.url)
        upload_files(request, form)

    if form.validate_on_submit():
        form_dict = request.form.to_dict()
        form_dict.pop('csrf_token')
        form_dict['ref_dir'] = '../media/refdir'
        form_dict['work_dir'] = '../media/workdir'
        form_dict['reference_file'] = form.reference_file.data.filename
        content = render_template('phame.tmpl', form=form_dict)
        with open('/phame_api01/phame_api01/media/config.ctl', 'w') as conf:
            conf.write(content)
        return redirect(url_for('run_phame', project=form_dict['project']))
    return render_template('input.html', title='Phame input', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}', 'remember_me={}'.format(
            form.username.data, form.remember_me.data
        ))
        return redirect(url_for('login'))
    return render_template('login.html', title='Sign In', form=form)


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
