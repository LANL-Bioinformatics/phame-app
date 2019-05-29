import json
import os
import shutil
import unittest
import io
import pandas as pd
from unittest.mock import patch, mock_open, Mock, MagicMock, PropertyMock
from flask_login import login_user, current_user
from flask import current_app, url_for
from project.tests.base import BaseTestCase
from project import db, create_app
from project.api.forms import InputForm
from project.api.models import User
from project.api.phame import link_files, get_data_type, symlink_uploaded_file, project_setup, get_config_property, \
    create_config_file, get_num_threads, get_exec_time, set_directories, get_file_counts, create_project_summary


app = create_app()

class FileObj():
    def __init__(self, filename):
        self.filename = filename

class PhameTest(BaseTestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    def setUp(self):
        self.project_dir = os.path.join('/test', 'mark', 'test1')
        self.ref_dir = os.path.join(self.project_dir, 'ref_dir')
        self.work_dir = os.path.join(self.project_dir, 'work_dir')
        self.upload_dir = current_app.config['UPLOAD_DIRECTORY']
        db.create_all()
        db.session.commit()

    def tearDown(self):
        if os.path.exists(self.project_dir):
            shutil.rmtree(self.project_dir)
        if os.path.exists(self.ref_dir):
            shutil.rmtree(self.ref_dir)
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        db.session.remove()
        db.drop_all()

    def add_user(self, username=None, email=None, password=None):
        usr = username if username else 'mark'
        eml = email if email else 'mcflynn617@gmail.com'
        pssword = password if password else  'test1'
        pssword2 = password if password else 'test1'
        with self.client:
            response = self.client.post(url_for('users.register'),
                                        data=json.dumps(
                                            {'username': usr,
                                             'email': eml,
                                             'password': pssword,
                                             'password2': pssword2
                                             }),
                                        content_type='application/json', )
        user = User.query.filter_by(username=usr).first()
        return user

    def login(self, username=None, password=None):
        username = username if username else 'mark'
        password = password if password else 'test1'
        self.client.post(url_for('users.login'), data=json.dumps(
            {'username': username, 'password': password}),
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

    def create_config_file(self):
        requests = Mock()
        form = InputForm(project='test1', ref_dir=self.ref_dir, work_dir=self.work_dir, reference='1',
                         reference_file='KJ660347.fasta', cds_snps='0', buildSNPdb='1', first_time='1', data_type='4',
                         reads='1', aligner='bowtie', tree='1', bootstrap='1', N='100', pos_select='2', code='0',
                         clean='0', threads='2', cutoff='0.2')
        print(form)
        # requests.post.side_effect = form
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        self.add_user()
        os.makedirs(self.project_dir, exist_ok=True)
        with self.client:
            self.login()
            create_config_file(form)

    def upload_files(self):
        self.add_user()
        file_list, fname_list = [], []
        for f in os.listdir(os.path.join('project', 'tests', 'fixtures')):
            file_list.append(open(os.path.join('project', 'tests', 'fixtures', f), 'rb'))
            fname_list.append(f)
        data = dict(file=file_list)
        files = self.create_paths(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark'),
                                  fname_list)
        with self.client:
            self.login()
            self.client.post(url_for('phame.upload'), data=data,
                             follow_redirects=True,
                             content_type='multipart/form-data')
        return files

    def test_symlink_files(self):
        self.add_user()
        os.makedirs(self.ref_dir, exist_ok=True)
        try:
            if os.path.exists(os.path.join(self.ref_dir, 'KJ660347.fasta')):
                os.remove(os.path.join(self.ref_dir, 'KJ660347.fasta'))
            if os.path.exists(os.path.join(self.ref_dir, 'KJ660347.gff')):
                os.remove(os.path.join(self.ref_dir, 'KJ660347.gff'))
            # current_app.config['PROJECT_DIRECTORY'] = self.project_dir
            data = dict(file=[open(
                os.path.join('project', 'tests', 'fixtures', 'KJ660347.fasta'),
                'rb'), open(
                os.path.join('project', 'tests', 'fixtures', 'KJ660347.gff'),
                'rb')])
            with self.client:
                self.login()
                self.client.post(url_for('phame.upload'), data=data,
                                 follow_redirects=True,
                                 content_type='multipart/form-data')
                self.assertTrue(os.path.exists(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark', 'KJ660347.fasta')))
                symlink_uploaded_file(self.ref_dir, 'KJ660347.fasta')
                self.assertTrue(os.path.join(self.ref_dir, 'KJ660347.fasta'))
                self.assertTrue(os.path.islink(os.path.join(self.ref_dir, 'KJ660347.fasta')))
        finally:
            if os.path.exists(os.path.join(self.ref_dir, 'KJ660347.fasta')):
                os.remove(os.path.join(self.ref_dir, 'KJ660347.fasta'))
            if os.path.exists(os.path.join(self.ref_dir, 'KJ660347.gff')):
                os.remove(os.path.join(self.ref_dir, 'KJ660347.gff'))

    def test_link_files(self):
        self.add_user()
        upload_files, complete_genomes_list, reads_list, contigs_list = [], [], [], []

        server_file_paths = \
            self.create_paths(os.path.join(self.project_dir, 'mark'),
                              os.listdir(os.path.join('project', 'tests',
                                                      'fixtures')))

        for f in os.listdir(os.path.join('project', 'tests', 'fixtures')):
            fo = FileObj(f)
            if f.endswith('.fna') or f.endswith('.gff'):
                complete_genomes_list.append(fo)
            if f.endswith('.fasta'):
                contigs_list.append(fo)
            if f.endswith('.fastq'):
                reads_list.append(fo)
            upload_files.append(open(os.path.join('project', 'tests', 'fixtures', f), 'rb'))

        try:
            with self.client:
                self.login()
                response = self.client.post(url_for('phame.upload'), data=dict(file=upload_files),
                                            follow_redirects=True,
                                            content_type='multipart/form-data')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(os.path.exists(os.path.exists(
                    os.path.join(current_app.config['UPLOAD_DIRECTORY'], 'mark',
                                 'KJ660347.fasta'))))
                self.assertTrue(os.path.exists(os.path.exists(
                    os.path.join(current_app.config['UPLOAD_DIRECTORY'], 'mark',
                                 'KJ660347.gff'))))
                self.assertTrue(os.path.exists(os.path.join(current_app.config['UPLOAD_DIRECTORY'], 'mark', 'KJ660347.fasta')))
                form_dict = dict(complete_genomes=complete_genomes_list, reads_files=reads_list,
                                 contigs_files=contigs_list)
                link_files(self.project_dir, self.ref_dir, self.work_dir, form_dict)
                self.assertTrue(os.path.exists(self.project_dir))
                self.assertTrue(os.path.islink(os.path.join(self.ref_dir, 'SRR3359589_R1.fastq')))
                self.assertTrue(os.path.exists(os.path.join(self.ref_dir, 'SRR3359589_R1.fastq')))
                self.assertTrue(os.path.islink(os.path.join(self.ref_dir, 'ZEBOV_2002_Ilembe.fna')))
                self.assertTrue(os.path.exists(os.path.join(self.ref_dir, 'ZEBOV_2002_Ilembe.fna')))
                self.assertTrue(os.path.exists(os.path.join(self.work_dir, 'KJ660347.contig')))
                self.assertTrue(os.path.islink(os.path.join(self.work_dir, 'KJ660347.contig')))
        finally:
            self.remove_files(server_file_paths)

    def test_upload(self):
        self.add_user()
        data = dict(file=[open(os.path.join('project', 'tests', 'fixtures', 'KJ660347.fasta'),'rb'),
                          open(os.path.join('project', 'tests', 'fixtures', 'KJ660347.gff'),'rb')])
        files = self.create_paths(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark'), ['KJ660347.fasta', 'KJ660347.gff'])
        print(current_app.config['PHAME_UPLOAD_DIR'])
        try:
            with self.client:
                self.login()
                self.remove_files(files)
                response = self.client.post(url_for('phame.upload'), data=data,
                                            follow_redirects=True,
                                            content_type='multipart/form-data')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(os.path.exists(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark', 'KJ660347.fasta')))
                self.assertTrue(os.path.exists(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark', 'KJ660347.gff')))
        finally:
            self.remove_files(files)

    def test_upload_files_list(self):
        self.add_user()
        data = dict(file=(io.BytesIO(b"abcdef"), 'test.jpg'))
        UPLOAD_DIRECTORY = current_app.config['UPLOAD_DIRECTORY']
        self.assertTrue(os.path.exists(os.path.join(UPLOAD_DIRECTORY, 'mark')))
        if os.path.exists(os.path.join(UPLOAD_DIRECTORY, 'mark', 'test.jpg')):
            os.remove(os.path.join(UPLOAD_DIRECTORY, 'mark', 'test.jpg'))
        try:
            with self.client:
                self.login()
                self.client.post(url_for('phame.upload'), data=data,
                                 follow_redirects=True,
                                 content_type='multipart/form-data')
                response = self.client.get(url_for('phame.upload_files_list'),)
                resp_data = json.loads(response.data.decode())
                self.assertEquals(response.status_code, 200)
                self.assertEquals(len(resp_data['uploads']), 1)
                self.assertEquals(resp_data['uploads'][0], 'test.jpg')
        finally:
            os.remove(os.path.join(UPLOAD_DIRECTORY, 'mark', 'test.jpg'))


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

    def test_get_data_type(self):
        options_list = ['0']
        value = get_data_type(options_list)
        self.assertEqual(value, '0')
        options_list = ['0', '1']
        value = get_data_type(options_list)
        self.assertEqual(value, '3')
        options_list = ['0', '2']
        value = get_data_type(options_list)
        self.assertEqual(value, '4')
        options_list = ['0', '2', '1']
        value = get_data_type(options_list)
        self.assertEqual(value, '6')

    @patch('project.api.phame.link_files')
    def test_project_setup(self, mock_link):
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        form_dict = dict(project='test1', reference='Random', reference_file=[])
        self.add_user()
        with self.client:
            self.login()
            proj_dir, ref_dir = project_setup(form_dict)
        mock_link.assert_called_once()
        self.assertEqual(proj_dir, '/test/mark/test1')
        self.assertEqual(ref_dir, '/test/mark/test1/refdir')

    @patch('project.api.phame.link_files')
    def test_project_setup_return_none(self, mock_link):
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        os.makedirs(os.path.join(current_app.config['PROJECT_DIRECTORY'], 'mark', 'test1', 'workdir', 'results'), exist_ok=True)
        with open(os.path.join(current_app.config['PROJECT_DIRECTORY'], 'mark',  'test1', 'workdir', 'results', 'test1.log'), 'wb') as fp:
            fp.write(b'test')
        form_dict = dict(project='test1', reference='Random', reference_file=[])
        self.add_user()
        with self.client:
            self.login()
            proj_dir, ref_dir = project_setup(form_dict)
        self.assertEqual(mock_link.call_count, 0)
        self.assertEqual(proj_dir, None)
        self.assertEqual(ref_dir, None)
        os.remove(os.path.join(current_app.config['PROJECT_DIRECTORY'], 'mark',  'test1', 'workdir', 'results', 'test1.log'))
        form_dict = dict(project='test1', reference='Given', reference_file=[])
        with self.client:
            self.login()
            proj_dir, ref_dir = project_setup(form_dict)
        self.assertEqual(mock_link.call_count, 0)
        self.assertEqual(proj_dir, None)
        self.assertEqual(ref_dir, None)

    def test_create_config_file(self):
        form_dict = dict(project='test1', ref_dir=self.ref_dir, work_dir=self.work_dir, reference='1',
                         reference_file='KJ660347.fasta', cds_snps='0', buildSNPdb='1', first_time='1', data_type='4',
                         reads='1', aligner='bowtie', tree='1', bootstrap='1', N='100', pos_select='2', code='0',
                         clean='0', threads='2', cutoff='0.2')
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        self.add_user()
        os.makedirs(self.project_dir, exist_ok=True)
        with self.client:
            self.login()
            create_config_file(form_dict)
        config_df = pd.read_csv(os.path.join(self.project_dir, 'config.ctl'), sep='=', header=None, names=['field', 'val'])
        config_df = config_df.loc[pd.notna(config_df['val']), :]
        config_df['field'] = config_df['field'].apply(lambda x: x.strip())
        value = config_df[config_df['field']=='project']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, 'test1')
        value = config_df[config_df['field']=='refdir']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '../test1/refdir/')
        value = config_df[config_df['field']=='workdir']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '../test1/workdir/')
        value = config_df[config_df['field']=='reference']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field']=='reffile']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, 'KJ660347.fasta')
        value = config_df[config_df['field']=='buildSNPdb']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field']=='FirstTime']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field']=='data']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '4')
        value = config_df[config_df['field']=='cdsSNPS']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '0')
        value = config_df[config_df['field']=='reads']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field']=='aligner']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, 'bowtie')
        value = config_df[config_df['field']=='tree']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field']=='bootstrap']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field']=='N']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '100')
        value = config_df[config_df['field']=='PosSelect']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '2')
        value = config_df[config_df['field']=='code']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '0')
        value = config_df[config_df['field']=='clean']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '0')
        value = config_df[config_df['field']=='threads']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '2')
        value = config_df[config_df['field']=='cutoff']['val'].values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '0.2')

    def test_get_config_property(self):
        self.create_config_file()
        value = get_config_property(self.project_dir, 'reference')
        self.assertEqual(value, '1')
        value = get_config_property(self.project_dir, 'N')
        self.assertEqual(value, '100')
        value = get_config_property(self.project_dir, 'refdir')
        self.assertEqual(value, '../test1/refdir/')
        value = get_config_property(self.project_dir, 'workdir')
        self.assertEqual(value, '../test1/workdir/')
        value = get_config_property(self.project_dir, 'project')
        self.assertEqual(value, 'test1')
        value = get_config_property(self.project_dir, 'reffile')
        self.assertEqual(value, 'KJ660347.fasta')
        value = get_config_property(self.project_dir, 'buildSNPdb')
        self.assertEqual(value, '1')
        value = get_config_property(self.project_dir, 'cutoff')
        self.assertEqual(value, '0.2')

    def test_get_num_threads(self):
        self.create_config_file()
        num_threads = get_num_threads(self.project_dir)
        self.assertEqual(num_threads, '2')

    def test_get_exec_time(self):
        os.makedirs(self.project_dir)
        with open(os.path.join(self.project_dir, 'time.log'), 'w') as fp:
            fp.write('86400000')
        exec_time = get_exec_time(self.project_dir)
        self.assertEqual(exec_time, '24:00:00')
        with open(os.path.join(self.project_dir, 'time.log'), 'w') as fp:
            fp.write('43200000')
        exec_time = get_exec_time(self.project_dir)
        self.assertEqual(exec_time, '12:00:00')

    def test_set_directories(self):
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        project_dir, workdir, results_dir, refdir = set_directories('mark', 'test1')
        self.assertEqual(project_dir, '/test/mark/test1')
        self.assertEqual(workdir, '/test/mark/test1/workdir')
        self.assertEqual(refdir, '/test/mark/test1/refdir')
        self.assertEqual(results_dir, '/test/mark/test1/workdir/results')

    def test_get_file_counts(self):
        os.makedirs(self.ref_dir)
        os.makedirs(self.work_dir)
        os.makedirs(os.path.join(self.work_dir, 'results'))
        files = self.upload_files()
        os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark', 'KJ660347.fasta'),
                   os.path.join(self.ref_dir, 'KJ660347.fasta'))
        os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark', 'SRR3359589_R1.fastq'),
                   os.path.join(self.ref_dir, 'SRR3359589_R1.fastq'))
        os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark', 'KJ660347.fasta'),
                   os.path.join(self.work_dir, 'KJ660347.contig'))
        reads_file_count, contigs_file_count, full_genome_file_count = get_file_counts(self.ref_dir, self.work_dir)
        self.assertEqual(full_genome_file_count, 1)
        self.assertEqual(reads_file_count, 1)
        self.assertEqual(contigs_file_count, 1)
        self.remove_files(files)
        self.remove_files([os.path.join(self.ref_dir, 'KJ660347.fasta'),
                           os.path.join(self.ref_dir, 'SRR3359589_R1.fastq'),
                           os.path.join(self.work_dir, 'KJ660347.contig')
                           ])

    def test_create_project_summary(self):
        self.add_user()
        with self.client:
            self.login()
            project_summary = create_project_summary('test1', 'finished', 2, 8, 4, 4, '12:00:00', 'KJ660347.fasta')
        self.assertEqual(project_summary['# of genomes analyzed'], 16)
        self.assertEqual(project_summary['# of contigs'], 4)
        self.assertEqual(project_summary['# of reads'], 8)
        self.assertEqual(project_summary['# of full genomes'], 4)
        self.assertEqual(project_summary['reference genome used'], 'KJ660347.fasta')
        self.assertEqual(project_summary['project name'], 'test1')
        self.assertEqual(project_summary['# of threads'], 2)
        self.assertEqual(project_summary['status'], 'finished')
        self.assertEqual(project_summary['execution time(h:m:s)'], '12:00:00')
        self.assertEqual(project_summary['delete'], '<input name="deleteCheckBox" type="checkbox" value=test1 unchecked">')

    def test_create_project_summary_public(self):
        self.add_user(username='public', email='public@example.com', password='public')
        with self.client:
            self.login(username='public', password='public')
            project_summary = create_project_summary('test1', 'finished', 2, 8, 4, 4, '12:00:00', 'KJ660347.fasta')
        self.assertEqual(project_summary['# of genomes analyzed'], 16)
        self.assertEqual(project_summary['# of contigs'], 4)
        self.assertEqual(project_summary['# of reads'], 8)
        self.assertEqual(project_summary['# of full genomes'], 4)
        self.assertEqual(project_summary['reference genome used'], 'KJ660347.fasta')
        self.assertEqual(project_summary['project name'], 'test1')
        self.assertEqual(project_summary['# of threads'], 2)
        self.assertEqual(project_summary['status'], 'finished')
        self.assertEqual(project_summary['execution time(h:m:s)'], '12:00:00')
        self.assertFalse('delete' in project_summary.keys())

    def test_delete_projects(self):
        os.makedirs(self.ref_dir)
        os.makedirs(self.work_dir)
        os.makedirs(os.path.join(self.work_dir, 'results'))
        files = self.upload_files()
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        with self.client:
            self.login()
            symlinked_files = []
            for f in os.listdir(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark')):
                symlink_uploaded_file(self.ref_dir, f)
                symlinked_files.append(os.path.join(self.ref_dir, f))
            self.assertTrue(os.path.exists(symlinked_files[0]))
            response = self.client.post(url_for('phame.delete_projects'), data=dict(deleteCheckBox=['test1']))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(os.path.exists(files[0]))
            for f in symlinked_files:
                self.assertFalse(os.path.exists(f))

    # def test_projects(self):



if __name__ == '__main__':
    unittest.main()


