import unittest
import json
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
import time
import os
from selenium.webdriver.common.by import By
import argparse
from selenium.webdriver.support import expected_conditions as EC
import sys
import yaml
import requests
import ast
from zipfile import ZipFile
sys.path.append(os.path.dirname(__file__))

class SiteTest(unittest.TestCase):

    """
        Functional tests using dev site
        Tests login, list, show and delete projects
    """

    def setUp(self):

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.project = 'test-project'
        self.project_subset = 'test-project_subset'
        chromeOptions = webdriver.ChromeOptions()
        prefs = {"download.default_directory": os.path.join(base_dir, 'project', 'tests', 'fixtures')}
        chromeOptions.add_experimental_option("prefs", prefs)
        chrome_driver = os.path.join(base_dir, 'tests', 'extra', 'chromedriver')
        self.driver = webdriver.Chrome(chrome_driver, options=chromeOptions)
        operator_data = os.path.join(base_dir, 'tests', 'fixtures', 'operator_data.yaml')
        if not os.path.exists(operator_data):
            print('site_data.yaml does not exist, copy example_site_data.yaml and add your credentials')
            sys.exit(0)
        with open(operator_data) as fp:
            creds = yaml.load(fp, Loader=yaml.FullLoader)

        if len(sys.argv) > 1:
            with open(os.path.join(base_dir, 'extra', 'fixtures', sys.argv[1])) as fp:
                site_data = yaml.safe_load(fp)
        else:
            with open(os.path.join(base_dir, 'tests', 'fixtures', 'site_data.yaml')) as fp:
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

    def login(self):
        self.logout()
        self.driver.get(f"{self.users_url}/login")
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys(self.operator_credentials['PHAME_USER_USERNAME'])
        password.send_keys(self.operator_credentials['PHAME_USER_PASSWORD'])
        self.driver.find_element_by_name("submit").click()

    def login_test_user(self):
        r = requests.post('http://localhost/users/api/login', json={'username': 'test_user', 'password': 'test_password'})
        return True if r.status_code == 200 else False



    def test_admin_login(self):
        self.admin_login()
        header = self.driver.find_element_by_xpath('// *[ @ id = "content"] / h1')
        self.assertIn('PhaME Input', header.text)

    def test_login(self):
        self.login()
        header = self.driver.find_element_by_xpath('// *[ @ id = "content"] / h1')
        self.assertIn('PhaME Input', header.text)

    def delete_user(self):
        self.admin_login()
        self.driver.get(self.users_url + "/delete")
        self.driver.find_element_by_xpath("//select[@id='manage_username']/option[text()='test_user']").click()
        self.driver.find_element_by_name("submit").click()

    def create_user(self):
        response = requests.get('http://localhost/users/users/name/test_user')
        if response.status_code == 200:
            self.delete_user()
            self.logout()
        self.driver.get(self.users_url + "/register")
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        password2 = self.driver.find_element_by_name("password2")
        email = self.driver.find_element_by_name("email")
        username.send_keys('test_user')
        password.send_keys('test_password')
        password2.send_keys('test_password')
        email.send_keys('test@test.com')
        self.driver.find_element_by_name("submit").click()

    def test_create_user(self):
        self.create_user()
        header = self.driver.find_element_by_xpath('/html/body/div[2]/h1') # /html/body/div[2]/h1
        self.assertIn('Sign In', header.text)
        self.delete_user()

    def test_delete_user(self):
        self.create_user()
        self.delete_user()
        self.driver.get(self.users_url + "/profile")

        user_names = self.driver.find_element_by_xpath("//select[@id='manage_username']")
        for user_name in user_names.text.split('\n'):
            self.assertFalse(user_name == 'test_user')

    def upload_files(self):
        # upload files
        self.driver.find_element_by_id("file-picker").send_keys(
            os.path.join(self.base_dir, 'tests', 'fixtures', 'KJ660347.fasta'))
        self.driver.find_element_by_id("file-picker").send_keys(
            os.path.join(self.base_dir, 'tests', 'fixtures', 'KJ660347.gff'))
        self.driver.find_element_by_id("file-picker").send_keys(
            os.path.join(self.base_dir, 'tests', 'fixtures',
                         'ZEBOV_2002_Ilembe.fna'))
        self.driver.find_element_by_id("file-picker").send_keys(
            os.path.join(self.base_dir, 'tests', 'fixtures',
                         'ZEBOV_2007_0Luebo.fna'))
        self.driver.find_element_by_css_selector("#upload-button").click()

    def remove_files(self):
        self.driver.get(self.url + '/input')
        self.driver.find_element_by_css_selector("#remove-button").click()

    def test_file_upload(self):
        self.create_user()
        self.login()
        self.upload_files()
        self.delete_user()

    def test_delete_file_uploads(self):
        self.create_user()
        self.login()
        self.remove_files()
        s = self.get_cookies()
        response = s.get('http://localhost/phame/files')
        self.assertEqual(response.json()['uploads'], [])
        self.delete_user()

    def get_flower_task_id(self, task_name):
        task_id = None
        tasks = requests.get('http://localhost:5555/api/tasks?state=STARTED')
        tasks_dict = tasks.json()
        for key, value in tasks_dict.items():
            values = ast.literal_eval(value['args'])
            if values[0] == task_name:
                task_id = key
        # if not task_id:
        #     tasks_all = requests.get('http://localhost:5555/api/tasks')
        #     tasks_all_dict = tasks_all.json()
        #     for key, value in tasks_all_dict.items():
        #         values = ast.literal_eval(value['args'])
        #         if values[0] == task_name:
        #             received_time = datetime.fromtimestamp(value['received'])
        return task_id

    def get_test_task_state(self, task_name):
        task_id = self.get_flower_task_id(task_name)
        state = None
        if task_id:
            state = 'STARTED'
            while state != 'SUCCESS':
                result = requests.get(f'http://localhost:5555/api/task/result/{task_id}')
                result_json = result.json()
                state = result_json['state']
        return state

    def test_run_project(self):
        self.login()

        self.driver.get(self.url + '/projects')
        try:
            test_project = self.driver.find_element_by_partial_link_text(self.project)
            if test_project:
                self.driver.find_element_by_xpath(
                    f"//input[@value='{self.project}']").click()
            self.driver.find_element_by_id("delete-button").click()
        except:
            pass
        self.driver.get(self.url + '/input')
        project = self.driver.find_element_by_name("project")
        project.send_keys(self.project)
        self.driver.find_element_by_xpath(("//*[@id='complete_genomes_div']/div/div[2]/span/div/button/span")).click()
        button = self.driver.find_element_by_xpath("//*[@id='complete_genomes_div']/div/div[2]/span/div/ul/li[1]/a/label/input")
        self.driver.implicitly_wait(10)
        button.click()
        self.driver.find_element_by_id("submit").click()
        if not self.get_test_task_state(self.project):
            self.assertFalse(True)
        self.driver.get(self.url + f'/display/mark/{self.project}')
        run_summary = self.driver.find_element_by_xpath('//*[@class="dataframe run_summary"]/thead').text
        self.assertIn('# of genomes analyzed # of contigs # of reads # of full genomes reference genome used project name', run_summary)
        self.assertEqual('0', self.driver.find_element_by_xpath('//*[@class="dataframe run_summary"]/tbody/tr/td[2]').text)
        self.assertEqual('3', self.driver.find_element_by_xpath(
            '//*[@class="dataframe run_summary"]/tbody/tr/td[1]').text)
        self.assertEqual('KJ660347', self.driver.find_element_by_xpath(
            '//*[@class="dataframe run_summary"]/tbody/tr/td[5]').text)
        self.assertEqual(self.project, self.driver.find_element_by_xpath(
            '//*[@class="dataframe run_summary"]/tbody/tr/td[6]').text)

        # Summary statistics
        self.assertEqual(self.driver.find_element_by_xpath('//*[@class="dataframe stats"]/tbody/tr[1]/td').text, 'KJ660347')
        self.assertEqual(self.driver.find_element_by_xpath('//*[@class="dataframe stats"]/tbody/tr[2]/td').text, '18959')
        self.assertEqual(self.driver.find_element_by_xpath('//*[@class="dataframe stats"]/tbody/tr[3]/td').text, '4')
        self.assertEqual(self.driver.find_element_by_xpath('//*[@class="dataframe stats"]/tbody/tr[4]/td').text, '18955')
        self.assertEqual(self.driver.find_element_by_xpath('//*[@class="dataframe stats"]/tbody/tr[5]/td').text, '764')

        #SNP pairwise matrix
        self.assertEqual(len(self.driver.find_element_by_xpath(
            '//*[@class="dataframe snp_pairwiseMatrix"]/thead/tr').text.split()),
                         3)
        self.assertEqual(self.driver.find_element_by_xpath(
            '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/th').text, 'KJ660347')
        self.assertEqual(self.driver.find_element_by_xpath(
            '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/td[1]').text, '0')
        self.assertEqual(self.driver.find_element_by_xpath(
            '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/td[2]').text, '593')
        self.assertEqual(self.driver.find_element_by_xpath(
            '//*[@class="dataframe snp_pairwiseMatrix"]/tbody/tr[1]/td[3]').text, '536')

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
        self.assertIn('KJ660347', self.driver.find_element_by_xpath('//*[@id="phylogram1"]').text)

        #subset
        self.driver.get(self.url + f'/display/mark/{self.project}')
        self.driver.find_element_by_partial_link_text("subset").click()
        queues = Select(self.driver.find_element_by_css_selector("#subset_files"))
        queues.select_by_visible_text("KJ660347.fasta")
        queues.select_by_visible_text("ZEBOV_2002_Ilembe.fna")
        self.driver.find_element_by_name("submit").click()
        # time.sleep(3)
        if not self.get_test_task_state(self.project_subset):
            self.assertFalse(True)
        self.driver.get(self.url + f'/display/mark/{self.project_subset}')

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
        self.driver.get(self.url + f'/display/mark/{self.project}')
        self.driver.find_element_by_partial_link_text('download').click()
        zip_name = f'_phame_api_media_mark_{self.project}_{self.project}.zip'
        with ZipFile(os.path.join(self.base_dir, 'project', 'tests', 'fixtures', zip_name)) as myzip:
            zip_list = myzip.namelist()
        zip_base_dir = os.path.join(self.project, 'workdir', 'results')
        self.assertIn(os.path.join(zip_base_dir, 'KJ660347_KJ660347.snpfilter'), zip_list)
        self.assertIn(os.path.join(zip_base_dir, 'KJ660347_KJ660347.gapfilter'), zip_list)
        self.assertIn(os.path.join(zip_base_dir, f'{self.project}.log'), zip_list)
        self.assertIn(os.path.join(zip_base_dir, f'{self.project}.error'), zip_list)
        self.assertIn(os.path.join(zip_base_dir, 'tables', f'{self.project}_snp_pairwiseMatrix.txt'), zip_list)
        self.assertIn(os.path.join(zip_base_dir, 'alignments', f'{self.project}_all_snp_alignment.fna'), zip_list)
        self.assertIn(os.path.join(zip_base_dir, 'stats', 'KJ660347_ZEBOV_2002_Ilembe.coords'), zip_list)
        os.remove(os.path.join(self.base_dir, 'project', 'tests', 'fixtures', zip_name))

        # delete test-project
        self.driver.get(self.url + '/projects')
        self.driver.find_element_by_xpath(f"//input[@value='{self.project}']").click()
        self.driver.find_element_by_xpath(f"//input[@value='{self.project_subset}']").click()
        self.driver.find_element_by_id("delete-button").click()

