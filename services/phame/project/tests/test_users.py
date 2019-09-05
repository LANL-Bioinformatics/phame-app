import json
import os
import unittest
from flask_login import login_user, current_user
from flask import current_app, url_for
from project.tests.base import BaseTestCase
from project import create_app
from project.api.models import User
from project import db
from project.tests.utils import add_user
app = create_app()


class UsersTest(BaseTestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    def add_user(self, username=None, email=None, password=None, is_admin=False):
        username = username if username else 'mark'
        eml = email if email else 'mcflynn617@gmail.com'
        pssword = password if password else 'test1'
        pssword2 = password if password else 'test1'
        user = User(username=username, email=eml, is_admin=is_admin)
        user.set_password(pssword)
        db.session.add(user)
        db.session.commit()
        return user

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
        user = add_user('test', 'test@test.com', 'test')
        with self.client:
            response = self.client.get(url_for('users.get_single_user', user_id=user.id))
            data = json.loads(response.data.decode())
            self.assertEqual(response.status_code, 200)
            self.assertIn('test', data['data']['username'])
            self.assertIn('test@test.com', data['data']['email'])
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
        add_user('test', 'test@test.com', 'test')
        add_user('test1', 'test1@test.com', 'test')
        with self.client:
            response = self.client.get(url_for('users.get_all_users'))
            data = json.loads(response.data.decode())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data['data']['users']), 2)
            self.assertIn('test', data['data']['users'][0]['username'])
            self.assertIn('test@test.com', data['data']['users'][0]
            ['email'])
            self.assertIn('test1', data['data']['users'][1]['username'])
            self.assertIn('test1@test.com', data['data']['users'][1]
            ['email'])
            self.assertIn('success', data['status'])

    def test_login(self):
        add_user('test', 'test@test.com', 'test')
        with self.client:
            response = self.client.post(url_for('users.login'),
                                        data=json.dumps(
                                            {'username': 'test',
                                             'password': 'test'
                                             }),
                                        content_type='application/json',
                                        )
            self.assertEquals(response.status_code, 302)
            self.assertEquals(current_user.username, 'test')
            self.assertEquals(current_user.email, 'test@test.com')
            self.assertIn('input', response.headers['Location'])

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
            self.assertEquals(response.status_code, 302)
            self.assertIn('login', response.headers['Location'])
            self.assertTrue(os.path.exists(os.path.join(PROJECT_DIRECTORY,
                                                        'mark')))
            self.assertTrue(os.path.exists(os.path.join(UPLOAD_DIRECTORY,
                                                        'mark')))
            user = User.query.filter_by(username='mark').first()
            self.assertEqual(user.email, 'mcflynn617@gmail.com')

    def test_login_bad_password(self):
        add_user('test', 'test@test.com', 'test')
        with self.client:
            response = self.client.post(url_for('users.login'),
                                        data=json.dumps(
                                            {'username': 'test',
                                             'password': 'testdfhfh1'
                                             }),
                                        content_type='application/json',
                                        )
            self.assertEquals(response.status_code, 302)
            self.assertIn('login', response.headers['Location'])

    def test_public_login(self):
        add_user('public', 'test@test.com', 'test')

        with self.client:
            response = self.client.post(url_for('users.login'),
                                        data=json.dumps(
                                            {'username': 'public',
                                             'password': 'test',
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
        add_user('test', 'test@test.com', 'test')
        user = User.query.filter_by(username='test').first()
        with self.client:
            login_user(user)
            self.assertTrue(current_user.is_authenticated)

    def test_login_public(self):
        add_user('public', 'test@test.com', 'test')
        user = User.query.filter_by(username='public').first()
        with self.client:
            login_user(user)
            self.assertTrue(current_user.is_authenticated)

    def test_profile_admin(self):

        add_user('test', 'test@test.com', 'test', is_admin=True)

        with self.client:
            self.client.post(url_for('users.login'),
                             data=json.dumps(
                                 {'username': 'test',
                                  'password': 'test'
                                  }),
                             content_type='application/json',
                             )
            user = User.query.filter_by(username='admin').first()
            print(f'user {user.username} is admin {user.is_admin}')
            response = self.client.get(url_for('users.profile'))
            self.assertIn('Username to view', str(response.data))

    def test_no_login_redirect(self):
        with self.client:
            response = self.client.get(url_for('phame.projects'))
            self.assertEquals(response.status_code, 302)
            self.assertIn('login', response.headers['Location'])

    def test_delete_user(self):
        admin = self.add_user(username='admin', email='admin@example.com',
                      password='test', is_admin=True)
        user = self.add_user()
        response = self.client.get(url_for('users.get_all_users'))
        data = json.loads(response.data.decode())
        self.assertEqual(len(data['data']['users']), 2)
        self.assertEqual(data['data']['users'][1]['username'], 'mark')
        with self.client:
            self.client.post(url_for('users.login'),
                             data=json.dumps(
                                 {'username': 'admin',
                                  'password': 'test'
                                  }),
                             content_type='application/json',
                             )
            response = self.client.post(url_for('users.delete_user'),
                             data=json.dumps(
                                 {'username': user.username
                                  }),
                             content_type='application/json',
                             )
            self.assertEqual(response.status_code, 200)
            response = self.client.get(url_for('users.get_all_users'))
            data = json.loads(response.data.decode())
            self.assertEqual(len(data['data']['users']), 1)
            deleted = True
            for user in data['data']['users']:
                if user['username'] == 'mark':
                    deleted = False
            self.assertTrue(deleted)

    def test_delete_user_not_admin(self):
        self.add_user(username='admin', email='admin@example.com',
                      password='test', is_admin=False)
        user = self.add_user()
        response = self.client.get(url_for('users.get_all_users'))
        data = json.loads(response.data.decode())
        self.assertEqual(len(data['data']['users']), 2)
        self.assertEqual(data['data']['users'][1]['username'], 'mark')
        with self.client:
            self.client.post(url_for('users.login'),
                             data=json.dumps(
                                 {'username': 'admin',
                                  'password': 'test'
                                  }),
                             content_type='application/json',
                             )
            response = self.client.post(url_for('users.delete_user'),
                             data=json.dumps(
                                 {'username': user.username
                                  }),
                             content_type='application/json',
                             )
            self.assertEqual(response.status_code, 422)
            response = self.client.get(url_for('users.get_all_users'))
            data = json.loads(response.data.decode())
            self.assertEqual(len(data['data']['users']), 2)
            deleted = True
            for user in data['data']['users']:
                if user['username'] == 'mark':
                    deleted = False
            self.assertFalse(deleted)

    def test_delete_user_does_not_exist(self):
        self.add_user(username='admin', email='admin@example.com',
                      password='test', is_admin=True)

        with self.client:
            self.client.post(url_for('users.login'),
                             data=json.dumps(
                                 {'username': 'admin',
                                  'password': 'test'
                                  }),
                             content_type='application/json',
                             )
            response = self.client.post(url_for('users.delete_user'),
                             data=json.dumps(
                                 {'username': 'fake_user'
                                  }),
                             content_type='application/json',
                             )
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data.decode())
            self.assertEqual(data['status'], 'fail')
            self.assertEqual(data['message'], 'Cannot delete user')


if __name__ == '__main__':
    unittest.main()
