import json
import os
import unittest
from flask_login import login_user, current_user
from flask import current_app, url_for
from project.tests.base import BaseTestCase
from project import create_app
from project.api.models import User
from project import db

app = create_app()


class UsersTest(BaseTestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    def add_user(self, username=None, email=None, password=None):
        user = username if username else 'mark'
        eml = email if email else 'mcflynn617@gmail.com'
        pssword = password if password else 'test1'
        pssword2 = password if password else 'test1'
        with self.client:
            response = self.client.post(url_for('users.register'),
                                        data=json.dumps(
                                            {'username': user,
                                             'email': eml,
                                             'password': pssword,
                                             'password2': pssword2
                                             }),
                                        content_type='application/json', )
            print(response.status_code)
        return User.query.filter_by(username=user).first()

    def create_app(self):
        # pass in test configuration
        app.config.from_object('project.config.TestingConfig')
        return app

    # def setUp(self):
    #     db.create_all()
    #     db.session.commit()
    #
    # def tearDown(self):
    #     db.session.remove()
    #     db.drop_all()

    #

    def test_set_password(self):
        new_user = User(username='test', email='test@example.com')
        new_user.set_password('mypassword')
        db.session.add(new_user)
        db.session.commit()
        user = User.query.filter_by(username='test').first()
        self.assertTrue(user.check_password('mypassword'))

    def test_single_user(self):
        """Ensure get single user behaves correctly."""
        user = self.add_user()
        with self.client:
            response = self.client.get(url_for('users.get_single_user', user_id=user.id))
            data = json.loads(response.data.decode())
            self.assertEqual(response.status_code, 200)
            self.assertIn('mark', data['data']['username'])
            self.assertIn('mcflynn617@gmail.com', data['data']['email'])
            self.assertIn('success', data['status'])

    def test_single_user_no_id(self):
        """Ensure error is thrown if an id is not provided."""
        with self.client:
            response = self.client.get(url_for('users.get_single_user', user_id='blah'))
            data = json.loads(response.data.decode())
            self.assertEqual(response.status_code, 404)
            self.assertIn('User does not exist', data['message'])
            self.assertIn('fail', data['status'])

    def test_single_user_incorrect_id(self):
        """Ensure error is thrown if the id does not exist."""
        with self.client:
            response = self.client.get(url_for('users.get_single_user', user_id=999))
            data = json.loads(response.data.decode())
            self.assertEqual(response.status_code, 404)
            self.assertIn('User does not exist', data['message'])
            self.assertIn('fail', data['status'])

    def test_all_users(self):
        self.add_user('mark', 'mcflynn617@gmail.com')
        self.add_user('fletcher', 'fletch@fletch.com')
        with self.client:
            response = self.client.get(url_for('users.get_all_users'))
            data = json.loads(response.data.decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data['data']['users']), 2)
            self.assertIn('mark', data['data']['users'][0]['username'])
            self.assertIn('mcflynn617@gmail.com', data['data']['users'][0]
            ['email'])
            self.assertIn('fletcher', data['data']['users'][1]['username'])
            self.assertIn('fletch@fletch.com', data['data']['users'][1]
            ['email'])
            self.assertIn('success', data['status'])

    def test_login(self):
        self.add_user()
        with self.client:
            response = self.client.post(url_for('users.login'),
                                        data=json.dumps(
                                            {'username': 'mark',
                                             'password': 'test1'
                                             }),
                                        content_type='application/json',
                                        )
            self.assertEquals(response.status_code, 302)
            self.assertEquals(current_user.username, 'mark')
            self.assertEquals(current_user.email, 'mcflynn617@gmail.com')
            # self.assertIn('input', response.headers['Location'])

    def test_logout(self):
            with self.client:
                response = self.client.get(url_for('users.logout'))
                self.assertEquals(response.status_code, 302)
                self.assertIn('login', response.headers['Location'])

    def test_register(self):
        PROJECT_DIRECTORY = current_app.config['PROJECT_DIRECTORY']
        UPLOAD_DIRECTORY = current_app.config['UPLOAD_DIRECTORY']
        with self.client:
            response = self.client.post(url_for('users.register'),
                                        data=json.dumps(
                                            {'username': 'mark',
                                             'email': 'mcflynn617@gmail.com',
                                             'password': 'test1',
                                             'password2': 'test1'
                                             }),
                                        content_type='application/json',)
            self.assertEquals(response.status_code, 200)
            # self.assertIn('login', response.headers['Location'])
            self.assertTrue(os.path.exists(os.path.join(PROJECT_DIRECTORY,
                                                        'mark')))
            self.assertTrue(os.path.exists(os.path.join(UPLOAD_DIRECTORY,
                                                        'mark')))
            user = User.query.filter_by(username='mark').first()
            self.assertEqual(user.email, 'mcflynn617@gmail.com')

    def test_login_bad_password(self):
        self.add_user('mark', 'mcflynn617@gmail.com', 'test1')
        with self.client:
            response = self.client.post(url_for('users.login'),
                                        data=json.dumps(
                                            {'username': 'mark',
                                             'password': 'testdfhfh1'
                                             }),
                                        content_type='application/json',
                                        )
            self.assertEquals(response.status_code, 302)
            self.assertIn('login', response.headers['Location'])

    def test_public_login(self):
        self.add_user(username='public', email='public@example.com',
                      password='test1')
        with self.client:
            response = self.client.post(url_for('users.login'),
                                        data=json.dumps(
                                            {'username': 'public',
                                             'password': 'test1',
                                             'public_login': True
                                             }),
                                        content_type='application/json',)
            self.assertEquals(response.status_code, 302)
            self.assertIn('projects', response.headers['Location'])

            response = self.client.get(url_for('users.get_all_users'))
            data = json.loads(response.data.decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['data']['users'][0]['username'], 'public')

    def test_login_user(self):
        self.add_user()
        user = User.query.filter_by(username='mark').first()
        with self.client:
            login_user(user)
            self.assertTrue(current_user.is_authenticated)

    def test_login_public(self):
        self.add_user(username='public', email='public@example.com',
                      password='test1')
        user = User.query.filter_by(username='public').first()
        with self.client:
            login_user(user)
            self.assertTrue(current_user.is_authenticated)

    def test_profile_admin(self):
        self.add_user(username='admin', email='admin@example.com',
                      password='test')

        with self.client:
            self.client.post(url_for('users.login'),
                             data=json.dumps(
                                 {'username': 'admin',
                                  'password': 'test'
                                  }),
                             content_type='application/json',
                             )
            response = self.client.get(url_for('users.profile'))
            self.assertIn('Username to view', str(response.data))

    def test_no_login_redirect(self):
        with self.client:
            response = self.client.get(url_for('phame.projects'))
            self.assertEquals(response.status_code, 302)
            self.assertIn('login', response.headers['Location'])

if __name__ == '__main__':
    unittest.main()
