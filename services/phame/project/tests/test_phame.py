import json
import os
import shutil
import unittest
import psutil
import io
import pandas as pd
import datetime
from bs4 import BeautifulSoup
from unittest.mock import patch, Mock, PropertyMock
from flask_login import current_user
from flask import current_app, url_for
from project.tests.base import BaseTestCase
from project import db, create_app
from project.api.forms import InputForm
from project.api.models import User, Project
from project.api.phame import link_files, get_data_type, \
    symlink_uploaded_file, project_setup, get_config_property, \
    create_config_file, get_num_threads, get_exec_time, set_directories, \
    get_file_counts, create_project_summary, get_log, get_system_specs, \
    get_log_mod_time, bytes2human, get_all_project_stats, update_stats


app = create_app()


class PhameTest(BaseTestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    def setUp(self):
        self.project_dir = os.path.join('/test', 'mark', 'test1')
        self.ref_dir = os.path.join(self.project_dir, 'refdir')
        self.work_dir = os.path.join(self.project_dir, 'workdir')
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
        pssword = password if password else 'test1'
        pssword2 = password if password else 'test1'
        print(f'usr {usr}')
        with self.client:
            response = self.client.post(url_for('users.register'),
                             data=json.dumps(
                                 {'username': usr,
                                  'email': eml,
                                  'password': pssword,
                                  'password2': pssword2
                                  }),
                             content_type='application/json', )
            # print(f'response {response.status_code} {response.data} ')
        user = User.query.filter_by(username=usr).first()
        print(f'add_user user {user}')

        return user

    def login(self, username=None, password=None):
        username = username if username else 'mark'
        password = password if password else 'test1'
        self.client.post(url_for('users.login'), data=json.dumps(
            {'username': username,
             'password': password}), content_type='application/json', )

    def create_file_paths(self):
        test_file = os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                 'mark', 'test1.fa')
        test_file2 = os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                  'mark', 'test2.fa')
        return [test_file, test_file2]

    def create_project(self, project, exec_time, end_time, status, num_threads, user):
        project_dir = os.path.join('/test', user.username, project)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
        self.create_config_file()
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        ref_dir = os.path.join(project_dir, 'refdir')
        work_dir = os.path.join(project_dir, 'workdir')
        os.makedirs(ref_dir)
        os.makedirs(os.path.join(work_dir, 'results'))
        print(f'ref_dir {ref_dir}')
        os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark',
                                'KJ660347.fasta'),
                   os.path.join(ref_dir, 'KJ660347.fasta'))
        os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark',
                                'SRR3359589_R1.fastq'),
                   os.path.join(ref_dir, 'SRR3359589_R1.fastq'))
        os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark',
                                'KJ660347.fasta'),
                   os.path.join(work_dir, 'KJ660347.contig'))
        with open(os.path.join(project_dir, 'time.log'), 'w') as fp:
            fp.write('86400000')
        with open(os.path.join(work_dir, 'results', 'test1.log'), 'w') as fp:
            fp.write('Tree complete')
        print(f'user {user.username}')
        db.session.add(Project(name=project,
                               end_time=end_time,
                               execution_time=exec_time, num_threads=num_threads,
                               status=status, user=user))
        db.session.commit()

    def create_paths(self, file_dir, files_list):
        output_file_list = []
        for f in files_list:
            output_file_list.append(os.path.join(file_dir, f))
        return output_file_list

    def remove_files(self, file_list):
        for file_name in file_list:
            if os.path.exists(file_name):
                os.remove(file_name)

    def create_config_file(self, field_dict=None):
        form = dict(project='test1', ref_dir=self.ref_dir,
                    work_dir=self.work_dir, reference='1',
                    reference_file='KJ660347.fasta', cds_snps='0',
                    buildSNPdb='1', first_time='1', data_type='4',
                    reads='1', aligner='bowtie', tree='1', bootstrap='1',
                    N='100', pos_select='2', code='0', clean='0', threads='2',
                    cutoff='0.2')
        if field_dict is not None:
            form[field_dict['field']] = field_dict['value']
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
            file_list.append(
                open(os.path.join('project', 'tests', 'fixtures', f), 'rb'))
            fname_list.append(f)
        data = dict(file=file_list)
        # print(current_app.config['PHAME_UPLOAD_DIR'])
        files = self.create_paths(
            os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark'),
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
                self.assertTrue(os.path.exists(
                    os.path.join(current_app.config['PHAME_UPLOAD_DIR'],
                                 'mark', 'KJ660347.fasta')))
                symlink_uploaded_file(self.ref_dir, 'KJ660347.fasta')
                self.assertTrue(os.path.join(self.ref_dir, 'KJ660347.fasta'))
                self.assertTrue(os.path.islink(os.path.join(self.ref_dir,
                                                            'KJ660347.fasta')))
        finally:
            if os.path.exists(os.path.join(self.ref_dir, 'KJ660347.fasta')):
                os.remove(os.path.join(self.ref_dir, 'KJ660347.fasta'))
            if os.path.exists(os.path.join(self.ref_dir, 'KJ660347.gff')):
                os.remove(os.path.join(self.ref_dir, 'KJ660347.gff'))

    def test_link_files(self):
        self.add_user()
        upload_files_list, complete_genomes_list = [], []
        reads_list, contigs_list = [], []

        server_file_paths = \
            self.create_paths(os.path.join(self.project_dir, 'mark'),
                              os.listdir(os.path.join('project', 'tests',
                                                      'fixtures')))

        for f in os.listdir(os.path.join('project', 'tests', 'fixtures')):
            if f.endswith('.fna') or f.endswith('.gff'):
                complete_genomes_list.append(f)
            if f.endswith('.fasta'):
                contigs_list.append(f)
            if f.endswith('.fastq'):
                reads_list.append(f)
            upload_files_list.append(open(os.path.join('project', 'tests',
                                                  'fixtures', f), 'rb'))

        try:
            with self.client:
                self.login()
                response = self.client.post(url_for('phame.upload'),
                                            data=dict(file=upload_files_list),
                                            follow_redirects=True,
                                            content_type='multipart/form-data')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(os.path.exists(os.path.exists(
                    os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                 'mark',
                                 'KJ660347.fasta'))))
                self.assertTrue(os.path.exists(os.path.exists(
                    os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                 'mark',
                                 'KJ660347.gff'))))
                self.assertTrue(os.path.exists(
                    os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                 'mark', 'KJ660347.fasta')))
                form_dict = InputForm(complete_genomes=complete_genomes_list,
                                      reads=reads_list, contigs=contigs_list)
                link_files(self.project_dir, self.ref_dir, self.work_dir,
                           form_dict)
                self.assertTrue(os.path.exists(self.project_dir))
                self.assertTrue(os.path.exists(
                    os.path.join(self.ref_dir, 'ZEBOV_2002_Ilembe.fna')))
                self.assertTrue(os.path.islink(
                    os.path.join(self.ref_dir, 'ZEBOV_2002_Ilembe.fna')))
                self.assertTrue(os.path.exists(
                    os.path.join(self.work_dir, 'KJ660347.contig')))
                self.assertTrue(os.path.islink(
                    os.path.join(self.work_dir, 'KJ660347.contig')))
                self.assertTrue(os.path.islink(
                    os.path.join(self.ref_dir, 'SRR3359589_R1.fastq')))
                self.assertTrue(os.path.exists(
                    os.path.join(self.ref_dir, 'SRR3359589_R1.fastq')))
        finally:
            self.remove_files(server_file_paths)

    def test_upload(self):
        self.add_user()
        data = dict(file=[open(os.path.join('project', 'tests', 'fixtures',
                                            'KJ660347.fasta'), 'rb'),
                          open(os.path.join('project', 'tests', 'fixtures',
                                            'KJ660347.gff'), 'rb')])
        files = self.create_paths(os.path.join(
            current_app.config['PHAME_UPLOAD_DIR'], 'mark'),
            ['KJ660347.fasta', 'KJ660347.gff'])
        print(current_app.config['PHAME_UPLOAD_DIR'])
        try:
            with self.client:
                self.login()
                self.remove_files(files)
                response = self.client.post(url_for('phame.upload'), data=data,
                                            follow_redirects=True,
                                            content_type='multipart/form-data')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(os.path.exists(
                    os.path.join(current_app.config['PHAME_UPLOAD_DIR'],
                                 'mark', 'KJ660347.fasta')))
                self.assertTrue(os.path.exists(
                    os.path.join(current_app.config['PHAME_UPLOAD_DIR'],
                                 'mark', 'KJ660347.gff')))
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
        form_dict = InputForm(project='test1', reference='Random',
                              reference_file=[])
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
        os.makedirs(os.path.join(current_app.config['PROJECT_DIRECTORY'],
                                 'mark', 'test1', 'workdir', 'results'),
                    exist_ok=True)
        with open(os.path.join(current_app.config['PROJECT_DIRECTORY'],
                               'mark', 'test1', 'workdir', 'results',
                               'test1.log'), 'wb') as fp:
            fp.write(b'test')
        form_dict = InputForm(project='test1', reference='Random',
                              reference_file=[])
        self.add_user()
        with self.client:
            self.login()
            proj_dir, ref_dir = project_setup(form_dict)
        self.assertEqual(mock_link.call_count, 0)
        self.assertEqual(proj_dir, None)
        self.assertEqual(ref_dir, None)
        os.remove(os.path.join(current_app.config['PROJECT_DIRECTORY'], 'mark',
                               'test1', 'workdir', 'results', 'test1.log'))

    def test_create_config_file(self):
        form = dict(project='test1', ref_dir=self.ref_dir,
                    work_dir=self.work_dir, reference='1',
                    reference_file='KJ660347.fasta', cds_snps='0',
                    buildSNPdb='1', first_time='1', data_type='4',
                    reads='1', aligner='bowtie', tree='1', bootstrap='1',
                    N='100', pos_select='2', code='0',
                    clean='0', threads='2', cutoff='0.2')
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        self.add_user()
        os.makedirs(self.project_dir, exist_ok=True)
        with self.client:
            self.login()
            create_config_file(form)
        config_df = pd.read_csv(os.path.join(self.project_dir, 'config.ctl'),
                                sep='=', header=None, names=['field', 'val'])
        config_df = config_df.loc[pd.notna(config_df['val']), :]
        config_df['field'] = config_df['field'].apply(lambda x: x.strip())
        value = \
            config_df[config_df['field'] == 'project']['val'].\
            values[0].strip().split('#')[0].strip()
        self.assertEqual(value, 'test1')
        value = config_df[config_df['field'] == 'refdir']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '../test1/refdir/')
        value = config_df[config_df['field'] == 'workdir']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '../test1/workdir/')
        value = config_df[config_df['field'] == 'reference']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field'] == 'reffile']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, 'KJ660347.fasta')
        value = config_df[config_df['field'] == 'buildSNPdb']['val'].\
            values[0].strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field'] == 'FirstTime']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field'] == 'data']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '4')
        value = config_df[config_df['field'] == 'cdsSNPS']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '0')
        value = config_df[config_df['field'] == 'reads']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field'] == 'aligner']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, 'bowtie')
        value = config_df[config_df['field'] == 'tree']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field'] == 'bootstrap']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '1')
        value = config_df[config_df['field'] == 'N']['val'].values[0].strip().\
            split('#')[0].strip()
        self.assertEqual(value, '100')
        value = config_df[config_df['field'] == 'PosSelect']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '2')
        value = config_df[config_df['field'] == 'code']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '0')
        value = config_df[config_df['field'] == 'clean']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '0')
        value = config_df[config_df['field'] == 'threads']['val'].values[0].\
            strip().split('#')[0].strip()
        self.assertEqual(value, '2')
        value = config_df[config_df['field'] == 'cutoff']['val'].values[0].\
            strip().split('#')[0].strip()
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

    def test_get_config_property_bad_value(self):
        value = None
        self.create_config_file(field_dict=
                            {'field': 'threads',
                             'value': '<input id="threads" name="threads"'
                                      ' type="text" value="2">  # Number '
                                      'of threads to use'})
        try:
            value = get_config_property(self.project_dir, 'threads')
        except IndexError as e:
            self.assertFalse(value)

    def test_get_num_threads(self):
        self.create_config_file()
        num_threads = get_num_threads(self.project_dir)
        self.assertEqual(num_threads, '2')

    def test_get_exec_time(self):
        os.makedirs(self.project_dir)
        with open(os.path.join(self.project_dir, 'time.log'), 'w') as fp:
            fp.write('86400000')
        exec_time = get_exec_time(self.project_dir)
        self.assertEqual(exec_time, 86400)
        with open(os.path.join(self.project_dir, 'time.log'), 'w') as fp:
            fp.write('43200000')
        exec_time = get_exec_time(self.project_dir)
        self.assertEqual(exec_time, 43200)

    def test_set_directories(self):
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        project_dir, workdir, results_dir, refdir = set_directories('mark',
                                                                    'test1')
        self.assertEqual(project_dir, '/test/mark/test1')
        self.assertEqual(workdir, '/test/mark/test1/workdir')
        self.assertEqual(refdir, '/test/mark/test1/refdir')
        self.assertEqual(results_dir, '/test/mark/test1/workdir/results')

    def test_get_file_counts(self):
        os.makedirs(self.ref_dir)
        os.makedirs(self.work_dir)
        os.makedirs(os.path.join(self.work_dir, 'results'))
        files = self.upload_files()
        os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark',
                                'KJ660347.fasta'),
                   os.path.join(self.ref_dir, 'KJ660347.fasta'))
        os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark',
                                'SRR3359589_R1.fastq'),
                   os.path.join(self.ref_dir, 'SRR3359589_R1.fastq'))
        os.symlink(os.path.join(current_app.config['PHAME_UPLOAD_DIR'], 'mark',
                                'KJ660347.fasta'),
                   os.path.join(self.work_dir, 'KJ660347.contig'))
        reads_file_count, contigs_file_count, full_genome_file_count = \
            get_file_counts(self.ref_dir, self.work_dir)
        self.assertEqual(full_genome_file_count, 1)
        self.assertEqual(reads_file_count, 1)
        self.assertEqual(contigs_file_count, 1)
        self.remove_files(files)
        self.remove_files([os.path.join(self.ref_dir, 'KJ660347.fasta'),
                           os.path.join(self.ref_dir, 'SRR3359589_R1.fastq'),
                           os.path.join(self.work_dir, 'KJ660347.contig')
                           ])

    def test_get_file_counts_no_directories(self):
        reads_file_count, contigs_file_count, full_genome_file_count = \
            get_file_counts(self.ref_dir, self.work_dir)
        self.assertEqual(full_genome_file_count, 0)
        self.assertEqual(reads_file_count, 0)
        self.assertEqual(contigs_file_count, 0)

    def test_create_project_summary(self):
        self.add_user()
        with self.client:
            self.login()
            project_summary = create_project_summary('test1', 'finished', 2, 8,
                                                     4, 4, '12:00:00', '2019-05-31 05:46:02',
                                                     'KJ660347.fasta')
        self.assertEqual(project_summary['# of genomes analyzed'], 16)
        self.assertEqual(project_summary['# of contigs'], 4)
        self.assertEqual(project_summary['# of reads'], 8)
        self.assertEqual(project_summary['# of full genomes'], 4)
        self.assertEqual(project_summary['reference genome used'],
                         'KJ660347.fasta')
        self.assertEqual(project_summary['project name'], 'test1')
        self.assertEqual(project_summary['# of threads'], 2)
        self.assertEqual(project_summary['status'], 'finished')
        self.assertEqual(project_summary['execution time(h:m:s)'], '12:00:00')
        self.assertEqual(project_summary['finish time'], '2019-05-31 05:46:02')
        self.assertEqual(
            project_summary['delete'],
            '<input name="deleteCheckBox" type="checkbox" '
            'value=test1 unchecked">')

    def test_create_project_summary_public(self):
        self.add_user(username='public', email='public@example.com',
                      password='public')
        with self.client:
            self.login(username='public', password='public')
            project_summary = create_project_summary('test1', 'finished', 2, 8,
                                                     4, 4, '12:00:00', '2019-05-31 05:46:02',
                                                     'KJ660347.fasta')
        self.assertEqual(project_summary['# of genomes analyzed'], 16)
        self.assertEqual(project_summary['# of contigs'], 4)
        self.assertEqual(project_summary['# of reads'], 8)
        self.assertEqual(project_summary['# of full genomes'], 4)
        self.assertEqual(project_summary['reference genome used'],
                         'KJ660347.fasta')
        self.assertEqual(project_summary['project name'], 'test1')
        self.assertEqual(project_summary['# of threads'], 2)
        self.assertEqual(project_summary['status'], 'finished')
        self.assertEqual(project_summary['execution time(h:m:s)'], '12:00:00')
        self.assertEqual(project_summary['finish time'], '2019-05-31 05:46:02')
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
            for f in \
                os.listdir(os.path.join(current_app.config['PHAME_UPLOAD_DIR'],
                                        'mark')):
                symlink_uploaded_file(self.ref_dir, f)
                symlinked_files.append(os.path.join(self.ref_dir, f))
            self.assertTrue(os.path.exists(symlinked_files[0]))
            response = self.client.post(url_for('phame.delete_projects'),
                                        data=dict(deleteCheckBox=['test1']))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(os.path.exists(files[0]))
            for f in symlinked_files:
                self.assertFalse(os.path.exists(f))

    def test_get_log(self):
        os.makedirs(os.path.join(self.work_dir, 'results'))
        shutil.copy(os.path.join('project', 'tests', 'fixtures', 'test1.log'),
                    os.path.join(self.work_dir, 'results', 'test1.log'))

        self.add_user()
        with self.client:
            self.login()
            response = self.client.get(url_for('phame.get_log',
                                               project='test1'))
            self.assertEqual(response.status_code, 200)
            resp_data = json.loads(response.data.decode())
            self.assertEquals(resp_data['log'], 'null')

    @patch('project.api.phame.send_mailgun')
    def test_notify(self, mock_send):
        current_app.config['SEND_NOTIFICATIONS'] = True
        self.add_user()
        with self.client:
            self.login()
            response = self.client.get(url_for('phame.notify',
                                               project='test1'))
            self.assertEqual(response.status_code, 302)
            mock_send.assert_called_with(
                'Your project test1 has finished running', 'test1')

    @patch('project.api.phame.send_mailgun')
    def test_not_notify(self, mock_send):
        current_app.config['SEND_NOTIFICATIONS'] = False
        self.add_user()
        with self.client:
            self.login()
            response = self.client.get(url_for('phame.notify',
                                               project='test1'))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(mock_send.call_count, 0)

    def test_display_file(self):
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        os.makedirs(os.path.join(self.work_dir, 'results'))
        shutil.copy(os.path.join('project', 'tests', 'fixtures', 'test1.log'),
                    os.path.join(self.work_dir, 'results', 'test1.log'))

        self.add_user()
        with self.client:
            self.login()
            response = self.client.get(url_for('phame.display_file',
            project='test1', filename='test1.log'))
            self.assertEqual(response.status_code, 200)
            # resp_data = json.loads(response.data.decode())
            # print(response.data)
            self.assertIn('Tree phylogeny complete', str(response.data))


    @patch('psutil.cpu_count')
    def test_get_system_specs(self, mock_cpu):
        total_mem = 4294967296
        human = bytes2human(total_mem)
        with patch.object(psutil, 'virtual_memory') as mock_mem:
            pt = Mock(total=total_mem)
            d = PropertyMock(return_value=total_mem)
            type(mock_mem).info = pt
            mock_mem.return_value = pt
            mock_cpu.return_value = 6
            specs = get_system_specs()
        print(specs)
        self.assertEqual(specs['num_cpus'], 6)
        self.assertEqual(specs['total_ram'], human)

    @patch('os.path.getmtime')
    def test_log_mod_time(self, mock_mtime):
        mock_mtime.return_value = 1559280752
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        os.makedirs(os.path.join(self.work_dir, 'results'))
        shutil.copy(os.path.join('project', 'tests', 'fixtures', 'test1.log'),
                    os.path.join(self.work_dir, 'results', 'test1.log'))

        self.add_user()
        with self.client:
            self.login()
            mod_time = get_log_mod_time('test1')
            print(mod_time)
        self.assertEqual(mod_time, '2019-05-31 05:32:32')

    @patch('project.api.phame.get_log_mod_time')
    def test_add_stats(self, mock_time):
        self.create_config_file()
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        os.makedirs(os.path.join(self.work_dir, 'results'))
        with open(os.path.join(self.project_dir, 'time.log'), 'w') as fp:
            fp.write('86400000')
        shutil.copy(os.path.join('project', 'tests', 'fixtures', 'test1.log'),
                    os.path.join(self.work_dir, 'results', 'test1.log'))
        self.add_user()
        mock_time.return_value = '2019-05-31 05:32:32'
        with self.client:
            self.login()
            response = self.client.post(url_for('phame.add_stats'),
                                        data=json.dumps({'project': 'test1',
                                                         'status': 'SUCCESS'}),
                                        content_type='application/json',)
        self.assertEqual(response.status_code, 201)
        resp_data = json.loads(response.data.decode())
        self.assertEqual(resp_data['status'], 'success')
        self.assertEqual(resp_data['message'], f'added project test1')
        project = Project.query.filter_by(name='test1').first()
        self.assertEqual(project.name, 'test1')
        self.assertEqual(project.end_time, datetime.datetime(2019, 5, 31, 5, 32, 32))
        self.assertEqual(project.num_threads, 2)
        self.assertEqual(project.execution_time, 86400)
        self.assertEqual(project.status, 'SUCCESS')

    @patch('project.api.phame.get_log_mod_time')
    def test_add_stats_bad_status(self, mock_time):
        self.create_config_file()
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        os.makedirs(os.path.join(self.work_dir, 'results'))
        with open(os.path.join(self.project_dir, 'time.log'), 'w') as fp:
            fp.write('86400000')
        shutil.copy(os.path.join('project', 'tests', 'fixtures', 'test1.log'),
                    os.path.join(self.work_dir, 'results', 'test1.log'))
        self.add_user()
        mock_time.return_value = '2019-05-31 05:32:32'
        with self.client:
            self.login()
            response = self.client.post(url_for('phame.add_stats'),
                                        data=json.dumps({'project': 'test1',
                                                         'status': 'SUCESSSS'}),
                                        content_type='application/json', )
        self.assertEqual(response.status_code, 201)
        resp_data = json.loads(response.data.decode())

    @patch('project.api.phame.get_log_mod_time')
    def test_add_stats_update(self, mock_time):
        self.create_config_file()
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        os.makedirs(os.path.join(self.work_dir, 'results'))
        with open(os.path.join(self.project_dir, 'time.log'), 'w') as fp:
            fp.write('86400000')
        shutil.copy(os.path.join('project', 'tests', 'fixtures', 'test1.log'),
                    os.path.join(self.work_dir, 'results', 'test1.log'))
        user = self.add_user()
        mock_time.return_value = '2019-05-31 05:32:32'
        db.session.add(Project(name='test1',
                               end_time=datetime.datetime(1970, 5, 31, 5, 32,
                                                          32),
                               execution_time=0, num_threads=2,
                               status='PENDING', user=user))
        db.session.commit()
        with self.client:
            self.login()
            response = self.client.post(url_for('phame.add_stats'),
                                        data=json.dumps({'project': 'test1',
                                                         'status': 'SUCCESS'}),
                                        content_type='application/json', )
        self.assertEqual(response.status_code, 201)
        resp_data = json.loads(response.data.decode())
        self.assertEqual(resp_data['message'], 'updated project test1')
        project = Project.query.filter_by(name='test1', user=user).first()
        self.assertEqual(project.status, 'SUCCESS')
        self.assertEqual(project.execution_time, 86400)

    @patch('project.api.phame.get_log_mod_time')
    def test_update_stats(self, mock_time):
        self.create_config_file()
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        os.makedirs(os.path.join(self.work_dir, 'results'))
        with open(os.path.join(self.project_dir, 'time.log'), 'w') as fp:
            fp.write('86400000')
        with open(os.path.join(self.work_dir, 'results', 'test1.log'), 'w') as fp:
            fp.write('Tree complete')
        mock_time.return_value = '2019-05-31 05:32:32'
        user = self.add_user()

        db.session.add(Project(name='test1',
                               end_time=datetime.datetime(1970, 5, 31, 5, 32,
                                                          32),
                               execution_time=0, num_threads=2,
                               status='PENDING', user=user))
        db.session.commit()
        with self.client:
            self.login()
            update_stats('test1')
        project = Project.query.filter_by(name='test1', user=user).first()
        self.assertEqual(project.end_time, datetime.datetime(2019, 5, 31, 5, 32, 32))
        self.assertEqual(project.execution_time, 86400)
        self.assertEqual(project.status, 'SUCCESS')

    def test_get_all_project_stats(self):
        user = self.add_user()
        db.session.add(Project(name='test1',
                               end_time=datetime.datetime(2019, 5, 31, 5, 32,
                                                          32),
                               execution_time=86400, num_threads=2,
                               status='SUCCESS', user=user))
        db.session.add(Project(name='test2',
                               end_time=datetime.datetime(2019, 5, 31, 5, 46,
                                                          2),
                               execution_time=43200, num_threads=4,
                               status='FAILURE', user=user))
        db.session.commit()
        with self.client:
            self.login()
            resp_data = get_all_project_stats()
        # print(resp_data)
        self.assertEqual(resp_data[0]['name'], 'test1')
        self.assertEqual(resp_data[0]['num_threads'], 2)
        self.assertEqual(resp_data[0]['status'], 'SUCCESS')
        self.assertEqual(resp_data[0]['end_time'], '2019-05-31 05:32:32')
        self.assertEqual(resp_data[0]['execution_time'], '24:00:00')
        self.assertEqual(resp_data[1]['name'], 'test2')
        self.assertEqual(resp_data[1]['num_threads'], 4)
        self.assertEqual(resp_data[1]['status'], 'FAILURE')
        self.assertEqual(resp_data[1]['end_time'], '2019-05-31 05:46:02')
        self.assertEqual(resp_data[1]['execution_time'], '12:00:00')

    def test_projects(self):
        user = self.add_user()
        self.create_project('test1',end_time=datetime.datetime(2019, 5, 31, 5, 32,32),
                            exec_time=86400, num_threads=2, status='SUCCESS', user=user)
        self.create_project('test2',end_time=datetime.datetime(2019, 5, 31, 5, 46,2),
                            exec_time=43200,
                            status='FAILURE',
                            num_threads=4, user=user)
        current_app.config['PROJECT_DIRECTORY'] = '/test'

        with self.client:
            self.login()
            response = self.client.get(url_for('phame.projects'))
        self.assertEqual(response.status_code, 200)
        # print(response.data)
        # with open('project/tests/fixtures/projects.html', 'wb') as fp:
        #     fp.write(response.data)
        # with open('project/tests/fixtures/projects.html', 'r') as fp:
        #     soup = BeautifulSoup(fp, 'html.parser')
        soup = BeautifulSoup(str(response.data), "html.parser")
        rows = soup.find_all('td')
        print(rows[:20])
        output = ['<td>test1</td>',
                  '<td>3</td>',
                  '<td>1</td>',
                  '<td>1</td>',
                  '<td></td>',
                  '<td>2</td>',
                  '<td>FAILURE</td>',
                  '<td>24:00:00</td>',
                  '<td>2019-05-31 05:32:32</td>',
                  '<td><input name="deleteCheckBox" type="checkbox" unchecked"="" value="test1"/></td>',
                  '<td>test2</td>',
                  '<td>3</td>',
                  '<td>1</td>',
                  '<td>1</td>',
                  '<td></td>',
                  '<td>4</td>',
                  '<td>FAILURE</td>',
                  '<td>12:00:00</td>',
                  '<td>2019-05-31 05:46:02</td>',
                  '<td><input name="deleteCheckBox" type="checkbox" unchecked"="" value="test2"/></td>']


        self.assertEqual(list(map(str, rows[:20])), output)
        self.assertEqual(len(soup.find_all('input')), 3)

    def test_projects_public(self):
        """Test public view only shows public projects and no delete checkbox is present"""
        public_user = self.add_user(username='public', email='public@example.com',
                                    password='public')
        print(f'public user added {public_user}')
        puser = User.query.filter_by(username='public').first()
        print(f'public user {puser}')
        user = self.add_user()
        self.create_project('private',end_time=datetime.datetime(2019, 5, 31, 5, 32,32),
                            exec_time=86400, num_threads=2, status='SUCCESS', user=user)

        self.create_project('public1',end_time=datetime.datetime(2019, 5, 31, 5, 32,32),
                            exec_time=86400, num_threads=2, status='SUCCESS', user=public_user)
        self.create_project('public2',end_time=datetime.datetime(2019, 5, 31, 5, 32,32),
                            exec_time=86400, num_threads=2, status='SUCCESS', user=public_user)

        with self.client:
            self.login(username='public', password='public')
            response = self.client.get(url_for('phame.projects'))
            self.assertEqual(response.status_code, 200)
            resp_data = str(response.data)
            public_soup = BeautifulSoup(resp_data, "html.parser")
            # with open('project/tests/fixtures/projects_public.html', 'wb') as fp:
            #     fp.write(response.data)
            # with open('project/tests/fixtures/projects_public.html', 'r') as fp:
            #     public_soup = BeautifulSoup(fp, 'html.parser')
            self.assertEqual(len(public_soup.find_all('input')), 0)

    def test_input_get(self):
        self.add_user()
        self.upload_files()
        files_list = []
        for f in os.listdir(os.path.join('project', 'tests', 'fixtures')):
            if f.endswith('.fna') or f.endswith('.gff') or f.endswith('.fasta'):
                files_list.append(f)
        with self.client:
            self.login()
            response = self.client.get(url_for('phame.input'))

        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(str(response.data), "html.parser")
        genomes = soup.find(id='complete_genomes').children
        files_list.sort()
        zip_list = zip(genomes, files_list)
        for genome, fname in zip_list:
            self.assertEqual(genome.get_text(), fname)

    def test_input_post(self):
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        print(current_app.config['PROJECT_DIRECTORY'])
        current_app.config['PHAME_UPLOAD_DIR'] = os.path.join('/', 'test', 'uploads')
        complete_genomes_list = []
        reads_list, contigs_list = [], []
        self.add_user()
        self.upload_files()
        for f in os.listdir(os.path.join('project', 'tests', 'fixtures')):
            if f.endswith('.fna') or f.endswith('.gff'):
                complete_genomes_list.append(f)
            if f.endswith('.fasta'):
                contigs_list.append(f)
            if f.endswith('.fastq'):
                reads_list.append(f)
        form = dict(complete_genomes=complete_genomes_list, reads=reads_list, contigs=contigs_list,
                    project='test1', reference_file=complete_genomes_list[0], data_type=[1])
        with self.client:
            self.login()
            response = self.client.post(url_for('phame.input'),
                                        data=dict(form))
        # with open('project/tests/fixtures/test_input.html', 'w') as fp:
        #     fp.write(str(response.data))
        self.assertEqual(response.status_code, 302)
        soup = BeautifulSoup(str(response.data), "html.parser")
        self.assertEqual(soup.find(style='color: red;'), None)

    @patch('project.api.phame.project_setup')
    def test_input_post_no_project_dir(self, mock_setup):
        self.add_user()
        self.upload_files()
        mock_setup.return_value = [None, None]

        form = dict(project='test1')
        with self.client:
            self.login()
            response = self.client.post(url_for('phame.input'), data=json.dumps(form), content_type='application/json', follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        mock_setup.assert_called_once()
        soup = BeautifulSoup(str(response.data), "html.parser")
        self.assertIn('Error: Project directory already exists', soup.find("p", class_='error').get_text())

    def test_input_post_form_validation(self):
        """Test form validation"""
        current_app.config['PROJECT_DIRECTORY'] = '/test'
        complete_genomes_list = []
        reads_list, contigs_list = [], []
        self.add_user()
        self.upload_files()
        # mock_setup.return_value = ['test1', 'test1/refdir']
        for f in os.listdir(os.path.join('project', 'tests', 'fixtures')):
            if f.endswith('.fna') or f.endswith('.gff'):
                complete_genomes_list.append(f)
            if f.endswith('.fasta'):
                contigs_list.append(f)
            if f.endswith('.fastq'):
                reads_list.append(f)
        form = dict(complete_genomes=complete_genomes_list, reads=reads_list, contigs=contigs_list,
                         project='test1', data_type=['1'])
        with self.client:
            self.login()
            response = self.client.post(url_for('phame.input'), data=json.dumps(form), content_type='application/json', follow_redirects=False)
        # with open('project/tests/fixtures/validation_error.html', 'w') as fp:
        #     fp.write(str(response.data))
        self.assertEqual(response.status_code, 200)
        # mock_setup.assert_called_once()
        soup = BeautifulSoup(str(response.data), "html.parser")
        red_tag = False
        for tag in soup.find_all('span'):
            if 'style="color: red;">[Not a valid choice]' in str(tag):
                red_tag = True
        self.assertTrue(red_tag)

    def test_num_results_files(self):
        user = self.add_user()
        self.create_project('test1', end_time=datetime.datetime(2019, 5, 31, 5, 32, 32),
                            exec_time=86400, num_threads=2, status='SUCCESS', user=user)

        data = dict(file=[open(
            os.path.join('project', 'tests', 'fixtures', 'KJ660347.fasta'),
            'rb'), open(
            os.path.join('project', 'tests', 'fixtures', 'KJ660347.gff'),
            'rb')])

if __name__ == '__main__':
    unittest.main()
