# services/phame/manage.py


from flask.cli import FlaskGroup
import unittest
import coverage
from project import create_app, db
from project.api.models import User

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
if __name__ == '__main__':
    cli()