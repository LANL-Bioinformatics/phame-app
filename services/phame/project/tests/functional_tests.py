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

sys.path.append(os.path.dirname(__file__))

class SiteTest(unittest.TestCase):

    """
        Functional tests using dev site
        Tests login, list, show and delete projects
    """

    def setUp(self):

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


    def admin_login(self):
        self.logout()
        self.driver.get(f"{self.users_url}/login")
        # element = WebDriverWait(self.driver, 10).until(
        #     lambda driver: self.driver.find_element_by_tag_name('a'))
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys(self.admin_credentials['PHAME_ADMIN_USERNAME'])
        password.send_keys(self.admin_credentials['PHAME_ADMIN_PASSWORD'])
        self.driver.find_element_by_name("submit").click()

    def logout(self):
        self.driver.get(self.users_url + '/logout')

    def login(self):
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys(self.operator_credentials['PHAME_OPERATOR_USERNAME'])
        password.send_keys(self.operator_credentials['PHAME_OPERATOR_PASSWORD'])

        self.driver.find_element_by_name("submit").click()

    def test_admin_login(self):
        self.logout()
        self.driver.get(f"{self.users_url}/login")
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys(self.admin_credentials['PHAME_ADMIN_USERNAME'])
        password.send_keys(self.admin_credentials['PHAME_ADMIN_PASSWORD'])
        self.driver.find_element_by_name("submit").click()
        header = self.driver.find_element_by_xpath('// *[ @ id = "content"] / h1')
        self.assertIn('PhaME Input', header.text)

    def test_login(self):
        self.logout()
        self.driver.get(f"{self.users_url}/login")
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys(self.operator_credentials['PHAME_USER_USERNAME'])
        password.send_keys(self.operator_credentials['PHAME_USER_PASSWORD'])
        self.driver.find_element_by_name("submit").click()
        header = self.driver.find_element_by_xpath('// *[ @ id = "content"] / h1')
        self.assertIn('PhaME Input', header.text)

    def delete_user(self):
        self.admin_login()
        self.driver.get(self.users_url + "/delete")
        self.driver.find_element_by_xpath("//select[@id='manage_username']/option[text()='test_user']").click()
        self.driver.find_element_by_name("submit").click()

    def create_user(self):
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

    def test_file_upload(self):
        self.create_user()
        self.driver.find_element_by_id("file-picker").send_keys(os.path.join('tests', 'fixtures', 'KJ660347.fasta'))
        self.driver.find_element_by_id("submit").click()  # file-picker
