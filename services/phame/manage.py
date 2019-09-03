# services/phame/manage.py

import os
from flask.cli import FlaskGroup
import unittest
import coverage
import time
from datetime import timedelta
from project import create_app, db
from project.api.models import User, Project
from project.api.phame import get_num_threads, get_exec_time

COV = coverage.coverage(
    branch=True,
    include='project/*',
    omit=[
        'project/tests/*',
        'project/config.py',
    ]
)
COV.start()
app = create_app()  # new
cli = FlaskGroup(create_app=create_app)


@cli.command()
def cov():
    """Runs the unit tests with coverage."""
    tests = unittest.TestLoader().discover('project/tests')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        COV.html_report()
        COV.erase()
        return 0
    return 1


@cli.command()
def recreate_db():
    db.drop_all()
    db.create_all()
    db.session.commit()


@cli.command('seed_db')
def seed_db():
    """seeds db password='test'"""
    password_hash = 'pbkdf2:sha256:50000$MP1SI8HV$d0a7a5403c7edaba6ca8c8bb69a925321488bcd090a80e0161383c20cb5ba943'
    db.session.add(User(username='mark', password_hash = password_hash, email='mcflynn617@gmail.com'))
    db.session.add(User(username='mflynn', password_hash = password_hash, email='mflynn@lanl.gov'))
    db.session.add(User(username='public', password_hash = password_hash, email='public@example.com'))
    db.session.add(User(username='admin', password_hash = password_hash, email='admin@example.com'))
    db.session.commit()


@cli.command()
def test():
    """ Runs the tests without code coverage"""
    tests = unittest.TestLoader().discover('project/tests', pattern='test*.py')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        return 0
    return 1


@cli.command()
def insert_projects():
    """ Insert projects into database """
    users = User.query.all()
    for user in users:
        proj_dir = os.path.join(app.config['PROJECT_DIRECTORY'], user.username)
        for project_name in os.listdir(proj_dir):
            num_threads = get_num_threads(os.path.join(proj_dir, project_name))
            exec_time = get_exec_time(os.path.join(proj_dir, project_name))
            if not os.path.exists(
                os.path.join(os.path.join(proj_dir, project_name, 'workdir', 'results'),
                             f'{project_name}.log')):
                project_task_status = 'FAILURE'
                mod_time = os.path.getmtime(os.path.join(proj_dir, project_name))
            else:
                project_task_status = 'SUCCESS'
                mod_time = os.path.getmtime(os.path.join(proj_dir, project_name, 'config.ctl'))
            start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))
            e_time = mod_time + exec_time
            end_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e_time))

            project = Project(name=project_name, user=user, num_threads=num_threads, execution_time=exec_time,
                              status=project_task_status, start_time=start_time, end_time=end_time)
            db.session.add(project)
            db.session.commit()


if __name__ == '__main__':
    cli()
