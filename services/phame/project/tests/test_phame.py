import json
import os
import shutil
import unittest
from unittest.mock import patch, mock_open, Mock, MagicMock, PropertyMock
from flask_login import login_user, current_user
from flask import current_app, url_for
from project.tests.base import BaseTestCase
from project import db, create_app
from project.api.models import User
from project.api.phame import link_files
import io
app = create_app()
class FileObj():
    def __init__(self, filename):
        self.filename = filename

class PhameTest(BaseTestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    def setUp(self):
        self.project_dir = '/test'
        self.ref_dir = '/test/ref_dir'
        self.work_dir = '/test/work_dir'
        self.upload_dir = current_app.config['UPLOAD_DIRECTORY']
        self.test_file = os.path.join(self.upload_dir,
                                      'mark', 'test1.fa')
        self.test_file2 = os.path.join(self.upload_dir,
                                       'mark', 'test2.fa')
        db.create_all()
        db.session.commit()

    def tearDown(self):
        # if os.path.exists(self.project_dir):
        #     shutil.rmtree(self.project_dir)
        # if os.path.exists(self.ref_dir):
        #     shutil.rmtree(self.ref_dir)
        # if os.path.exists(self.work_dir):
        #     shutil.rmtree(self.work_dir)
        # if os.path.exists(self.work_dir):
        #     shutil.rmtree(self.work_dir)
        db.session.remove()
        db.drop_all()

    def add_user(self, username=None, email=None, password=None):
        usr = username if username else 'mark'
        eml = email if email else 'mcflynn617@gmail.com'
        pssword = password if password else  'test1'
        pssword2 = password if password else 'test1'
        with self.client:
            response = self.client.post('/users/register',
                                        data=json.dumps(
                                            {'username': usr,
                                             'email': eml,
                                             'password': pssword,
                                             'password2': pssword2
                                             }),
                                        content_type='application/json', )
        user = User.query.filter_by(username=usr).first()
        return user

    def login(self):
        self.client.post(url_for('users.login'), data=json.dumps(
            {'username': 'mark', 'password': 'test1'}),
                         content_type='application/json', )

    def create_file_paths(self):
        test_file = os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                 'mark', 'test1.fa')
        test_file2 = os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                  'mark', 'test2.fa')
        return [test_file, test_file2]

    def create_paths(self, file_dir, files_list):
        output_file_list = []
        for f in files_list:
            output_file_list.append(os.path.join(file_dir, f))
        return output_file_list

    def remove_files(self, file_list):
        for file_name in file_list:
            if os.path.exists(file_name):
                os.remove(file_name)

    def test_link_files(self):
        self.add_user()
        data = dict(file=[open(
            os.path.join('project', 'tests', 'fixtures', 'KJ660347.fasta'),
            'rb'), open(
            os.path.join('project', 'tests', 'fixtures', 'KJ660347.gff'),
            'rb')])
        server_file_paths = \
            self.create_paths(self.project_dir,
                              os.listdir(os.path.join('project', 'tests',
                                                      'fixtures')))
        files, upload_files = [], []
        for f in os.listdir(os.path.join('project', 'tests', 'fixtures')):
            fo = FileObj(f)
            files.append(fo)
            upload_files.append(open(os.path.join('project', 'tests', 'fixtures', f), 'rb'))
        try:
            with self.client:
                self.login()
                response = self.client.post(url_for('phame.upload'), data=data,
                                            follow_redirects=True,
                                            content_type='multipart/form-data')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(os.path.exists(os.path.exists(
                    os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                 'KJ660347.fasta'))))
                self.assertTrue(os.path.exists(os.path.exists(
                    os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                 'KJ660347.gff'))))
                self.assertTrue(os.path.exists(os.path.join(current_app.config['UPLOAD_DIRECTORY'], 'KJ660347.fasta')))
                form_dict = dict(complete_genomes=files, reads_files=[],
                                 contigs_files=[])
                link_files(self.project_dir, self.ref_dir, self.work_dir, form_dict)
                self.assertTrue(os.path.exists(self.project_dir))
                self.assertTrue(os.path.islink(os.path.join(self.ref_dir,
                                                            'KJ660347.fasta')))
                self.assertTrue(os.path.exists(os.path.join(self.ref_dir,
                                                            'KJ660347.fasta')))
        finally:
            self.remove_files(server_file_paths)

    def test_upload(self):
        self.add_user()
        # data = dict(file=[(io.BytesIO(b"abcdef"), 'test1.fa'),(io.BytesIO(b"abcdef"), 'test2.fa')])
        data = dict(file=[open(os.path.join('project', 'tests', 'fixtures', 'KJ660347.fasta'),'rb'),
                          open(os.path.join('project', 'tests', 'fixtures', 'KJ660347.gff'),'rb')])
        files = self.create_file_paths()
        try:
            with self.client:
                self.login()
                self.remove_files(files)
                response = self.client.post(url_for('phame.upload'), data=data,
                                            follow_redirects=True,
                                            content_type='multipart/form-data')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(os.path.exists(os.path.join(current_app.config['UPLOAD_DIRECTORY'], 'KJ660347.fasta')))
                self.assertTrue(os.path.exists(os.path.join(current_app.config['UPLOAD_DIRECTORY'], 'KJ660347.gff')))
        finally:
            self.remove_files(files)

    def test_upload_files_list(self):
        self.add_user()
        data = dict(file=(io.BytesIO(b"abcdef"), 'test.jpg'))
        UPLOAD_DIRECTORY = current_app.config['UPLOAD_DIRECTORY']
        self.assertTrue(os.path.exists(os.path.join(UPLOAD_DIRECTORY, 'mark')))
        with self.client:
            self.login()
            self.client.post(url_for('phame.upload'), data=data,
                             follow_redirects=True,
                             content_type='multipart/form-data')
            response = self.client.get(url_for('phame.upload_files_list'),)
            resp_data = json.loads(response.data.decode())
            self.assertEquals(response.status_code, 200)
            self.assertEquals(len(resp_data['uploads']), 2)
            self.assertEquals(resp_data['uploads'][0], 'test.jpg')

    def test_remove_files(self):
        self.add_user()
        data = dict(file=(io.BytesIO(b"abcdef"), 'test.jpg'))
        UPLOAD_DIRECTORY = current_app.config['UPLOAD_DIRECTORY']
        self.assertTrue(os.path.exists(os.path.join(UPLOAD_DIRECTORY, 'mark')))
        with self.client:
            self.login()
            test_file = os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                     current_user.username, 'test.jpg')
            self.client.post(url_for('phame.upload'), data=data,
                             follow_redirects=True,
                             content_type='multipart/form-data')
            self.assertTrue(os.path.exists(test_file))
            response = self.client.post(url_for('phame.remove_files'))

            self.assertEquals(response.status_code, 200)

            resp_data = json.loads(response.data.decode())
            self.assertEquals(len(resp_data['uploads']), 0)
            self.assertFalse(os.path.exists(test_file))


if __name__ == '__main__':
    unittest.main()


# class TestPhameService(BaseTestCase):
#
    def setUp(self):
        self.project_dir = '/test'
        self.ref_dir = '/test/ref_dir'
        self.work_dir = '/test/work_dir'

    def tearDown(self):
        if os.path.exists(self.project_dir):
            shutil.rmtree(self.project_dir)
        if os.path.exists(self.ref_dir):
            shutil.rmtree(self.ref_dir)
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)



