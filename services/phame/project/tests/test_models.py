import json
import os
import unittest
from datetime import datetime
from flask_login import login_user, current_user
from flask import current_app, url_for
from project.tests.base import BaseTestCase
from project import create_app
from project.api.models import User, Project
from project import db

app = create_app()


def add_user():
    new_user = User(username='test_user', email='test@example.com')
    db.session.add(new_user)
    db.session.commit()
    return User.query.filter_by(username='test_user').first()

class ModelsTest(BaseTestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    def setUp(self):
        db.create_all()
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        # pass in test configuration
        app.config.from_object('project.config.TestingConfig')
        return app

    def test_set_password(self):
        new_user = User(username='test_user', email='test@example.com')
        new_user.set_password('password')
        db.session.add(new_user)
        db.session.commit()
        user = User.query.filter_by(username='test_user').first()
        self.assertTrue(user.check_password('password'))

    def test_user_to_json(self):
        add_user()
        user = User.query.filter_by(username='test_user').first()
        user_json = user.to_json()
        self.assertEqual(user_json['id'], 1)
        self.assertEqual(user_json['username'], 'test_user')
        self.assertEqual(user_json['email'], 'test@example.com')
        self.assertEqual(user_json['active'], True)

    def test_project_seconds_to_time(self):
        user = add_user()
        new_project = Project(name='test', user=user, execution_time=60)
        db.session.add(new_project)
        db.session.commit()
        project = Project.query.filter_by(name='test').first()
        self.assertEqual(project.convert_seconds_to_time(), '0:01:00')

    def test_project_to_json(self):
        user = add_user()
        new_project = Project(name='test', user=user, start_time=datetime(2019, 6, 25, 12, 32, 45),
                              end_time=datetime(2019, 6, 25, 12, 32, 56))
        db.session.add(new_project)
        db.session.commit()
        project = Project.query.filter_by(name='test').first()
        project_json = project.to_json()
        self.assertEqual(project_json['name'], 'test')
        self.assertEqual(project_json['status'], 'PENDING')
        self.assertEqual(project_json['num_threads'], 2)
        self.assertEqual(project_json['execution_time'], '0:00:00')
        self.assertEqual(project_json['start_time'], '2019-06-25 12:32:45')
        self.assertEqual(project_json['end_time'], '2019-06-25 12:32:56')

    def test_user_projects(self):
        user = add_user()
        new_project1 = Project(name='test1', user=user, start_time=datetime(2019, 6, 25, 12, 32, 45),
                               end_time=datetime(2019, 6, 25, 12, 32, 56))
        db.session.add(new_project1)
        db.session.commit()
        new_project2 = Project(name='test2', user=user, start_time=datetime(2019, 6, 25, 12, 32, 45),
                               end_time=datetime(2019, 6, 25, 12, 32, 56))
        db.session.add(new_project2)
        db.session.commit()
        projects = Project.query.all()
        self.assertEqual(projects[0].user_id,1)
        self.assertEqual(projects[1].user_id,1)
        self.assertEqual(len(user.projects), 2)
        self.assertEqual(user.projects[0].name, 'test1')
        self.assertEqual(user.projects[0].start_time, datetime(2019, 6, 25, 12, 32, 45))
