import unittest
import json
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
import time
import re
import os
from selenium.webdriver.common.by import By
import argparse
from selenium.webdriver.support import expected_conditions as EC
import sys
import yaml
import requests
import ast
import argparse
from zipfile import ZipFile
sys.path.append(os.path.dirname(__file__))


class SiteTest(unittest.TestCase):

    """
        Functional tests using dev site
        Tests login, list, show and delete projects
    """

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project = 'test-project'
        self.project_subset = 'test-project_subset'
        chromeOptions = webdriver.ChromeOptions()
        prefs = {"download.default_directory": os.path.join(self.base_dir, 'tests',
                                                            'extra')}
        chromeOptions.add_experimental_option("prefs", prefs)
        chrome_driver = os.path.join(self.base_dir, 'tests', 'extra',
                                     'chromedriver')
        self.driver = webdriver.Chrome(chrome_driver, options=chromeOptions)
        operator_data_file = os.environ['OPERATOR_DATA'] if \
            'OPERATOR_DATA' in os.environ.keys() \
            else os.path.join(self.base_dir, 'tests', 'fixtures',
                              'operator_data.yaml')

        if not os.path.exists(operator_data_file):
            print('site_data.yaml does not exist, '
                  'copy example_operator_data.yaml and add your credentials')
            sys.exit(0)

        with open(operator_data_file) as fp:
            creds = yaml.load(fp, Loader=yaml.FullLoader)

        site_date_file = os.environ['SITE_DATA'] if 'SITE_DATA' in \
                                                    os.environ.keys() \
            else os.path.join(self.base_dir, 'tests', 'fixtures', 'site_data.yaml')
        if not os.path.exists(site_date_file):
            print('site_data.yaml does not exist, '
                  'copy example_site_data.yaml and add your credentials')
            sys.exit(0)

        with open(site_date_file, 'r') as fp:
            site_data = yaml.safe_load(fp)

        self.url = site_data['site_params']['PHAME_TEST_URL']
        self.users_url = site_data['site_params']['PHAME_USERS_URL']
        self.operator_credentials = creds['user_credentials']
        self.admin_credentials = creds['admin_credentials']

    def tearDown(self):
        self.driver.get(self.users_url + '/logout')
        self.driver.close()

    def get_cookies(self):
        """ Add logged in users cookies to session for future requests"""
        s = requests.session()
        for cookie in self.driver.get_cookies():
            c = {cookie['name']: cookie['value']}
            s.cookies.update(c)
        return s

    def admin_login(self):
        self.logout()
        self.driver.get(f"{self.users_url}/login")
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys(self.admin_credentials['PHAME_ADMIN_USERNAME'])
        password.send_keys(self.admin_credentials['PHAME_ADMIN_PASSWORD'])
        self.driver.find_element_by_name("submit").click()

    def logout(self):
        self.driver.get(self.users_url + '/logout')

    def login(self, username=None, password=None):
        self.logout()
        if not username:
            username = self.operator_credentials['PHAME_USER_USERNAME']
        if not password:
            password = self.operator_credentials['PHAME_USER_PASSWORD']
        self.driver.get(f"{self.users_url}/login")
        username_box = self.driver.find_element_by_name("username")
        password_box = self.driver.find_element_by_name("password")
        username_box.clear()
        username_box.send_keys(username)
        password_box.send_keys(password)
        # self.driver.find_element_by_xpath(
        #     "//input[@id='remember_me']").click()
        self.driver.find_element_by_name("submit").click()

    @staticmethod
    def login_test_user(self):
        r = requests.post('http://localhost/users/api/login',
                          json={'username': 'test_user',
                                'password': 'test_password'})
        return True if r.status_code == 200 else False

    def delete_user(self):
        self.admin_login()
        self.driver.get(self.users_url + "/delete")
        self.driver.find_element_by_xpath(
            "//select[@id='manage_username']/option[text()='test_user']"
        ).click()
        self.driver.find_element_by_name("submit").click()

    def remove_test_user(self):
        # Check to see if test_user has been created, if so, delete
        response = requests.get(f'{self.users_url}/users/name/test_user')
        if response.status_code == 200:
            self.delete_user()
            self.logout()

    def create_user(self, user_name='test_user', email_address='test@test.com',
                    delete_duplicate=True):
        """
        Creates test_user
        :return:
        """
        if user_name == 'test_user' and delete_duplicate:
            self.remove_test_user()
        self.driver.get(self.users_url + "/register")
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        password2 = self.driver.find_element_by_name("password2")
        email = self.driver.find_element_by_name("email")
        username.send_keys(user_name)
        password.send_keys('test_password')
        password2.send_keys('test_password')
        email.send_keys(email_address)
        self.driver.find_element_by_name("submit").click()

    def append_gz(self, gz_files, upload_files):
        for z_file in gz_files:
            if z_file in upload_files:
                upload_files[upload_files.index(z_file)] = upload_files[
                                                                   upload_files.index(
                                                                       z_file)] + '.gz'
        return upload_files

    def upload_files(self, *files_list):
        """
        Uploads a default list of complete genome files plus an arbitrary list of optional files
        Checks which files have been already uploaded and waits until the files that have not yet been uploaded
        have finished uploading
        :param files_list:
        :return:
        """
        # add complete genome files
        default_files = ['KJ660347.fasta', 'KJ660347.gff', 'ZEBOV_2002_Ilembe.fna', 'ZEBOV_2007_0Luebo.fna']
        files_to_upload_list = [*default_files, *files_list]
        files_to_upload = set(files_to_upload_list)
        s = self.get_cookies()
        response = s.get(self.url + '/files')
        print(response.status_code)
        print(response.json())

        # get list of .gz files to upload
        gz_files = []
        for f in files_to_upload_list:
            if f.endswith('.gz'):
                gz_files.append('.'.join(f.split('.')[:-1]))
            # else:
            #     gz_files.append(re.sub('[^A-Za-z0-9]+', '_',
            #                       os.path.splitext(f)[0]) + \
            #                os.path.splitext(f)[1])

        already_uploaded_files_list = response.json()['uploads']

        # find any corresponding uncompressed files already uploaded and append gz
        already_uploaded_files_list = self.append_gz(gz_files, already_uploaded_files_list)

        # get list of files that still need to be uploaded by taking the difference between
        # the list of files that must be uploaded and the list of files that have already been
        # uploaded
        already_uploaded_files = set(already_uploaded_files_list)
        upload_files_list = list(files_to_upload.difference(already_uploaded_files))

        for item in upload_files_list:
            self.driver.find_element_by_id("file-picker").send_keys(
                os.path.join(self.base_dir, 'tests', 'fixtures', item))

        self.driver.find_element_by_css_selector("#upload-button").click()
        done_uploading = False
        while not done_uploading:
            response = s.get(self.url + '/files')
            uploaded_files = response.json()['uploads']
            uploaded_files = self.append_gz(gz_files, uploaded_files)
            if len(set(files_to_upload_list).difference(set(uploaded_files))) == 0:
                done_uploading = True
        s.close()
        time.sleep(2)

    def remove_files(self):
        self.driver.get(self.url + '/input')
        self.driver.find_element_by_css_selector("#remove-button").click()

    def run_project(self, *options, delete_duplicate=True):

        # remove test_project if it already exists
        if delete_duplicate:
            self.driver.get(self.url + '/projects')
            try:
                test_project = self.driver.find_element_by_partial_link_text(
                    self.project)
                if test_project:
                    self.driver.find_element_by_xpath(
                        f"//input[@value='{self.project}']").click()
                self.driver.find_element_by_id("delete-button").click()
            except:
                pass
        self.driver.get(self.url + '/input')
        project = self.driver.find_element_by_name("project")
        project.send_keys(self.project)
        if 'complete' in options:
            self.driver.find_element_by_xpath(
                "//button/span[@class='multiselect-selected-text']").click()
            self.driver.find_element_by_xpath(
                "//input[@value='multiselect-all']").click()
        if 'contig' in options:
            self.driver.find_element_by_xpath(
                "//input[@id='data_type-1']").click()
            self.driver.find_element_by_xpath("//select[@id='contigs']/following-sibling::div/button/span[@class='multiselect-selected-text']").click()
            self.driver.find_element_by_xpath(
                "//input[@value='multiselect-all']").click()
        if 'read' in options:
            self.driver.find_element_by_xpath(
                "//input[@id='data_type-2']").click()
            self.driver.find_element_by_xpath(
                "//select[@id='reads_type']").click()
            self.driver.find_element_by_xpath("//select[@id='reads']/following-sibling::div/button/span[@class='multiselect-selected-text']").click()
            # self.driver.find_element_by_xpath(
            #     "//input[@value='multiselect-all']").click()
            self.driver.find_element_by_xpath(
                "//input[@value='SRR3359589_R1.fastq']").click()
            self.driver.find_element_by_xpath(
                "//input[@value='SRR3359589_R2.fastq']").click()
        self.driver.find_element_by_id("submit").click()

    def test_admin_login(self):
        self.admin_login()
        header = self.driver.find_element_by_xpath('//*[@id="content"]/h1')
        self.assertIn('PhaME Input', header.text)
        profile_username = self.driver.find_element_by_xpath(
            "//*[@class='navbar-text']").text
        self.assertEqual(profile_username, self.admin_credentials['PHAME_ADMIN_USERNAME'])

    def test_login(self):
        self.login()
        header = self.driver.find_element_by_xpath('//*[@id="content"]/h1')
        self.assertIn('PhaME Input', header.text)
        profile_username = self.driver.find_element_by_xpath(
            "//*[@class='navbar-text']").text
        self.assertEqual(profile_username, self.operator_credentials['PHAME_USER_USERNAME'])

    def test_login_invalid(self):
        self.logout()
        self.driver.get(f"{self.users_url}/login")
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys('fake_user')
        password.send_keys('fake_password')
        self.driver.find_element_by_name("submit").click()
        self.assertEqual(self.driver.find_element_by_xpath(
            "/html/body/div[2]/ul/li").text, 'Invalid username or password')

    def test_login_remember(self):
        self.logout()
        self.driver.get(f"{self.users_url}/login")
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys(self.operator_credentials['PHAME_USER_USERNAME'])
        password.send_keys(self.operator_credentials['PHAME_USER_PASSWORD'])
        self.driver.find_element_by_xpath(
            "//input[@id='remember_me']").click()
        self.driver.find_element_by_name("submit").click()
        s = self.get_cookies()
        self.assertTrue('remember_token' in s.cookies._cookies['']['/'].keys())
        header = self.driver.find_element_by_xpath('//*[@id="content"]/h1')
        self.assertIn('PhaME Input', header.text)
        profile_username = self.driver.find_element_by_xpath(
            "//*[@class='navbar-text']").text
        self.assertEqual(profile_username, self.operator_credentials['PHAME_USER_USERNAME'])


    def test_public_login(self):
        self.create_user(user_name='public',
                         email_address='public@example.com')
        self.driver.get(f"{self.users_url}/login")
        self.driver.find_element_by_xpath(
            "//input[@id='public_login']").click()
        self.driver.find_element_by_name("submit").click()
        self.assertEqual(self.driver.find_element_by_partial_link_text(
            'iqtree-test').text, 'iqtree-test')
        self.assertEqual(self.driver.find_element_by_xpath(
            "//table[@class='dataframe run summary']/tbody/tr/td[2]").text,
                         '9')
        self.assertEqual(self.driver.find_element_by_xpath(
            "//table[@class='dataframe run summary']/tbody/tr/td[5]").text,
                         'KJ660347')
        self.assertEqual(self.driver.find_element_by_xpath(
            "//table[@class='dataframe run summary']/tbody/tr/td[7]").text,
                         'SUCCESS')
        self.driver.find_element_by_partial_link_text('iqtree-test').click()
        self.assertEqual(self.driver.find_element_by_xpath(
            "//table[@class='dataframe run_summary']/tbody/tr/td[1]").text,
                         '9')

        # self.assertEqual()

    def test_create_user(self):
        self.create_user()
        header = self.driver.find_element_by_xpath('/html/body/div[2]/h1')
        self.assertIn('Sign In', header.text)
        self.delete_user()

    def test_create_user_invalid_username(self):
        self.create_user('test user')
        self.assertEqual(self.driver.find_element_by_xpath(
            '//label[@for="username"]/following-sibling::span').text,
                         '[Username cannot contain spaces]')

    def test_create_user_duplicate_username_password(self):
        self.create_user()
        self.create_user(delete_duplicate=False)
        self.assertEqual(self.driver.find_element_by_xpath(
            '//label[@for="username"]/following-sibling::span').text,
                         '[Please use a different username.]')
        self.assertEqual(self.driver.find_element_by_xpath(
            '//label[@for="email"]/following-sibling::span').text,
                         '[Please use a different email address.]')

    def test_delete_user(self):
        self.create_user()
        self.delete_user()
        self.driver.get(self.users_url + "/profile")

        user_names = self.driver.find_element_by_xpath(
            "//select[@id='manage_username']")
        for user_name in user_names.text.split('\n'):
            self.assertFalse(user_name == 'test_user')

    def test_file_upload(self):
        self.create_user()
        self.login()
        self.remove_files()
        self.upload_files()
        self.assertIn('KJ660347.fasta', self.driver.find_element_by_xpath("//textarea[@id='uploads']").text)
        self.delete_user()

    def test_upload_gz_file(self):
        # self.create_user()
        self.login()
        self.remove_files()
        self.upload_files('GCA_000010485.contig.gz')
        self.assertIn('GCA_000010485.contig', self.driver.find_element_by_xpath("//textarea[@id='uploads']").text)
        self.assertNotIn('GCA_000010485.contig.gz', self.driver.find_element_by_xpath("//textarea[@id='uploads']").text)
        # self.delete_user()

    def test_upload_special_char_file(self):
        # self.create_user()
        self.login()
        self.remove_files()
        self.upload_files('C.diff_ATCC9689.fna')
        self.assertIn('C_diff_ATCC9689.fna', self.driver.find_element_by_xpath("//textarea[@id='uploads']").text)

    def test_delete_file_uploads(self):
        self.create_user()
        self.login()
        s = self.get_cookies()
        self.remove_files()
        response = s.get(self.url + '/files')
        s.close()
        self.assertEqual(response.json()['uploads'], [])
        self.delete_user()

    @staticmethod
    def get_flower_task_id(task_name):
        """ Gets task id from flower celery monitor"""
        task_id = None
        tasks = requests.get('http://localhost:5555/api/tasks?state=STARTED')
        tasks_dict = tasks.json()
        for key, value in tasks_dict.items():
            args = ast.literal_eval(value['args'])
            if args[0] == task_name:
                task_id = key
        return task_id

    def wait_task_success(self, project):
        """ Gets task state for running project """
        # task_id = self.get_flower_task_id(task_name)
        # state = None
        # if task_id:
        state = 'STARTED'
        s = self.get_cookies()
        while state != 'SUCCESS':
            result = s.get(f'{self.url}/stats/{project}')
            result_json = result.json()
            state = result_json['data']
        s.close()
        return state

    def delete_projects(self, projects_list):
        self.driver.get(self.url + '/projects')
        for project in projects_list:
            try:
                self.driver.find_element_by_xpath(
                    f"//input[@value='{project}']").click()
            except:
                pass
        self.driver.find_element_by_id("delete-button").click()

    def test_run_project_duplicate(self):
        self.login()
        self.delete_projects([self.project, self.project_subset])
        self.run_project('complete')
        time.sleep(6)
        self.run_project('complete', delete_duplicate=False)
        self.assertEqual(self.driver.find_element_by_xpath(
            '//p[@class="error"]').text,
                         'Error: Project directory already exists')
        # delete test-project
        self.delete_projects([self.project])

    def test_run_project(self):
        try:
            self.login()
            self.upload_files()
            self.delete_projects([self.project, self.project_subset])
            self.run_project('complete')
            self.wait_task_success(self.project)
            self.driver.get(self.url + f"/display/{self.operator_credentials['PHAME_USER_USERNAME']}/{self.project}")
            run_summary = self.driver.find_element_by_xpath(
                '//*[@class="dataframe run_summary"]/thead').text
            self.assertIn('# of genomes analyzed # of contigs # of reads # of full genomes reference genome used project name', run_summary)
            self.assertEqual('0', self.driver.find_element_by_xpath(
                '//*[@class="dataframe run_summary"]/tbody/tr/td[2]').text)
            self.assertEqual('3', self.driver.find_element_by_xpath(
                '//*[@class="dataframe run_summary"]/tbody/tr/td[1]').text)
            self.assertEqual('KJ660347', self.driver.find_element_by_xpath(
                '//*[@class="dataframe run_summary"]/tbody/tr/td[5]').text)
            self.assertEqual(self.project, self.driver.find_element_by_xpath(
                '//*[@class="dataframe run_summary"]/tbody/tr/td[6]').text)

            # Summary statistics
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[1]/td').text, 'KJ660347')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[2]/td').text, '18959')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[3]/td').text, '4')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[4]/td').text, '18955')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[5]/td').text, '764')

            #SNP pairwise matrix
            self.assertEqual(len(self.driver.find_element_by_xpath(
                '//*[@class="dataframe snp_pairwiseMatrix"]/thead/tr').text.split()),
                             3)
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/th').text,
                             'KJ660347')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/td[1]').text,
                             '0')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/td[2]').text,
                             '593')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/td[3]').text,
                             '536')

            # Genome Length
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe genome_lengths"]/tbody/tr[1]/td[1]').text,
                             'KJ660347')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe genome_lengths"]/tbody/tr[1]/td[2]').text,
                             '18959')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe genome_lengths"]/tbody/tr[2]/td[1]').text,
                             'ZEBOV_2002_Ilembe')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe genome_lengths"]/tbody/tr[2]/td[2]').text,
                             '18958')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe genome_lengths"]/tbody/tr[3]/td[1]').text,
                             'ZEBOV_2007_0Luebo')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe genome_lengths"]/tbody/tr[3]/td[2]').text,
                             '18958')

            # trees
            self.driver.find_element_by_partial_link_text(
                'fasttree').click()
            self.driver.find_element_by_xpath("//*[@id='phylogram1']")
            self.assertIn('KJ660347', self.driver.find_element_by_xpath(
                '//*[@id="phylogram1"]').text)

            #subset
            self.driver.get(self.url + f"/display/{self.operator_credentials['PHAME_USER_USERNAME']}/{self.project}")
            self.driver.find_element_by_partial_link_text("subset").click()
            queues = Select(self.driver.find_element_by_css_selector(
                "#subset_files"))
            queues.select_by_visible_text("KJ660347.fasta")
            queues.select_by_visible_text("ZEBOV_2002_Ilembe.fna")
            self.driver.find_element_by_name("submit").click()
            self.wait_task_success(self.project_subset)
            self.driver.get(self.url + f"/display/{self.operator_credentials['PHAME_USER_USERNAME']}/{self.project_subset}")

            # Run Summary
            self.assertEqual('0', self.driver.find_element_by_xpath(
                '//*[@class="dataframe run_summary"]/tbody/tr/td[2]').text)
            self.assertEqual('2', self.driver.find_element_by_xpath(
                '//*[@class="dataframe run_summary"]/tbody/tr/td[1]').text)
            self.assertEqual('KJ660347', self.driver.find_element_by_xpath(
                '//*[@class="dataframe run_summary"]/tbody/tr/td[5]').text)
            self.assertEqual(self.project_subset, self.driver.find_element_by_xpath(
                '//*[@class="dataframe run_summary"]/tbody/tr/td[6]').text)

            # Summary statistics
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[1]/td').text, 'KJ660347')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[2]/td').text, '18959')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[3]/td').text, '4')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[4]/td').text, '18955')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe stats"]/tbody/tr[5]/td').text, '590')

            # SNP pairwise matrix
            self.assertEqual(len(self.driver.find_element_by_xpath(
                '//*[@class="dataframe snp_pairwiseMatrix"]/thead/tr').text.split()), 2)
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/th').text,
                             'KJ660347')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/td[1]').text,
                             '0')
            self.assertEqual(self.driver.find_element_by_xpath(
                '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/td[2]').text,
                             '593')

            # trees
            self.driver.find_element_by_partial_link_text(f'{self.project}_all.fasttree').click()
            self.driver.find_element_by_xpath("//*[@id='phylogram1']")
            self.assertIn('KJ660347', self.driver.find_element_by_xpath(
                '//*[@id="phylogram1"]').text)
            self.driver.find_element_by_partial_link_text(f'{self.project}').click()
            self.driver.find_element_by_partial_link_text(
                f'{self.project_subset}_all.fasttree').click()
            self.driver.find_element_by_xpath("//*[@id='phylogram1']")
            self.assertIn('KJ660347', self.driver.find_element_by_xpath(
                '//*[@id="phylogram1"]').text)

            # test download
            self.driver.get(self.url + f"/display/{self.operator_credentials['PHAME_USER_USERNAME']}/{self.project}")
            self.driver.find_element_by_partial_link_text('download').click()
            zip_name = f"_phame_api_media_{self.operator_credentials['PHAME_USER_USERNAME']}_{self.project}_{self.project}.zip"
            time.sleep(2)
            with ZipFile(os.path.join(self.base_dir,  'tests', 'extra', zip_name)) as myzip:
                zip_list = myzip.namelist()
            zip_base_dir = os.path.join(self.project, 'workdir', 'results')
            self.assertIn(os.path.join(zip_base_dir, 'KJ660347_KJ660347.snpfilter'), zip_list)
            self.assertIn(os.path.join(zip_base_dir, 'KJ660347_KJ660347.gapfilter'), zip_list)
            self.assertIn(os.path.join(zip_base_dir, f'{self.project}.log'), zip_list)
            self.assertIn(os.path.join(zip_base_dir, f'{self.project}.error'), zip_list)
            self.assertIn(os.path.join(zip_base_dir, 'tables', f'{self.project}_snp_pairwiseMatrix.txt'), zip_list)
            self.assertIn(os.path.join(zip_base_dir, 'alignments', f'{self.project}_all_snp_alignment.fna'), zip_list)
            self.assertIn(os.path.join(zip_base_dir, 'stats', 'KJ660347_ZEBOV_2002_Ilembe.coords'), zip_list)
            os.remove(os.path.join(self.base_dir, 'tests', 'extra', zip_name))

            # delete test-project
            self.delete_projects([self.project, self.project_subset])
        finally:
            self.delete_projects([self.project, self.project_subset])

    def test_run_project_reads(self):
        self.login()
        self.upload_files('SRR3359589_R1.fastq', 'SRR3359589_R2.fastq')
        self.run_project('complete', 'read')


if __name__ == '__main__':
    unittest.main()
