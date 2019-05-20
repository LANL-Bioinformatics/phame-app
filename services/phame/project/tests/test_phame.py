import json
import os
import shutil
import unittest
from unittest.mock import patch, mock_open, Mock, MagicMock, PropertyMock
from flask_login import login_user, current_user
from flask import current_app
from project.tests.base import BaseTestCase
from project import db, create_app
from project.api.models import User
from project.api import phame

app = create_app()

class PhameTest(BaseTestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True




if __name__ == '__main__':
    unittest.main()


# class TestPhameService(BaseTestCase):
#
#     # def setUp(self):
#     #     self.project_dir = '/test'
#     #     self.ref_dir = '/test/ref_dir'
#     #     self.work_dir = '/test/work_dir'
#     #
#     # def tearDown(self):
#     #     if os.path.exists(self.project_dir):
#     #         shutil.rmtree(self.project_dir)
#     #     if os.path.exists(self.ref_dir):
#     #         shutil.rmtree(self.ref_dir)
#     #     if os.path.exists(self.work_dir):
#     #         shutil.rmtree(self.work_dir)
#
#     def add_user(self, username=None, email=None, password=None):
#         with self.client:
#             response = self.client.post('/phame/register',
#                                         data=json.dumps(
#                                             {'username': 'mark',
#                                              'email': 'mcflynn617@gmail.com',
#                                              'password': 'test1',
#                                              'password2': 'test1'
#                                              }),
#                                         content_type='application/json', )
#
#     def test_logout(self):
#         with self.client:
#             response = self.client.get('/phame/logout')
#             self.assertEquals(response.status_code, 302)
#             self.assertIn('login', response.headers['Location'])
#
#     def test_register(self):
#         PROJECT_DIRECTORY = os.path.join('/phame_api', 'media')
#         UPLOAD_DIRECTORY = os.path.join('static', 'uploads')
#         with self.client:
#             response = self.client.post('/phame/register',
#                                         data=json.dumps(
#                                             {'username': 'mark',
#                                              'email': 'mcflynn617@gmail.com',
#                                              'password': 'test1',
#                                              'password2': 'test1'
#                                              }),
#                                         content_type='application/json',)
#             self.assertEquals(response.status_code, 302)
#             self.assertIn('login', response.headers['Location'])
#             self.assertTrue(os.path.exists(os.path.join(PROJECT_DIRECTORY, 'mark')))
#             self.assertTrue(os.path.exists(os.path.join(UPLOAD_DIRECTORY, 'mark')))
#             user = User.query.filter_by(username='mark').first()
#             self.assertEqual(user.email, 'mcflynn617@gmail.com')
#

#
#     def test_profile_admin(self):
#         with self.client:
#             self.add_user('admin', 'admin@example.com',
#                      'test')
#             self.client.post('/phame/login',
#                              data=json.dumps(
#                                  {'username': 'admin',
#                                  'password': 'test'
#                                  }),
#                              content_type='application/json',
#                              )
#             response = self.client.get('/phame/profile')
#             self.assertIn('Username to view', str(response.data))

    # @patch('project.api.forms.InputForm')
    #     # def test_link_files(self, mock_form):
    #     #     with self.client:
    #     #         user = add_user('mark', 'mcflynn617@gmail.com', 'test1')
    #     #         login_user(user)
    #     #         mock_form.complete_genomes.data = ['test_genome.fa']
    #     #
    #     #         phame.link_files(self.project_dir, self.ref_dir, self.work_dir, mock_form)
    #     #         self.assertTrue(os.path.exists(self.project_dir))
