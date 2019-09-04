import unittest
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
import time
import os
from selenium.webdriver.common.by import By
from urlparse import *
import argparse
from selenium.webdriver.support import expected_conditions as EC
import sys
print sys.path
import yaml

sys.path.append(os.path.dirname(__file__))

class SiteTest(unittest.TestCase):

    """
        Functional tests using dev site
        Tests login, list, show and delete projects
    """

    def setUp(self):

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        chromeOptions = webdriver.ChromeOptions()
        prefs = {"download.default_directory": os.path.join(base_dir,'cm','tests')}
        chromeOptions.add_experimental_option("prefs", prefs)
        chrome_driver = os.path.join(base_dir, 'extra', 'chromedriver')
        self.driver = webdriver.Chrome('/Devel/cmdb/extra/chromedriver', chrome_options=chromeOptions)
        operator_data = os.path.join(base_dir, 'extra', 'fixtures', 'operator_data.yaml')
        if not os.path.exists(operator_data):
            print('operator_data.yaml does not exist, copy example_operator_data.yaml and add your credentials')
            sys.exit(0)
        with open(operator_data) as fp:
            creds = yaml.safe_load(fp)

        if len(sys.argv) > 1:
            with open(os.path.join(base_dir, 'extra', 'fixtures', sys.argv[1])) as fp:
                site_data = yaml.safe_load(fp)
        else:
            with open(os.path.join(base_dir, 'extra', 'fixtures', 'test_sgp_data.yaml')) as fp:
                site_data = yaml.safe_load(fp)

        self.url = site_data['site_params']['PHAME_TEST_URL']
        self.operator_credentials = creds['operator_credentials']
        self.admin_credentials = creds['admin_credentials']

    def admin_login(self):
        self.admin_logout()
        self.driver.get(self.url)
        element = WebDriverWait(self.driver, 10).until(
            lambda driver: self.driver.find_element_by_tag_name('a'))
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys(self.admin_credentials['PHAME_ADMIN_USERNAME'])
        password.send_keys(self.admin_credentials['PHAME_ADMIN_PASSWORD'])
        self.driver.find_element_by_name("submitbutton").click()


    def admin_logout(self):
        self.driver.get(self.url + '/accounts/logout')

    def login(self):
        username = self.driver.find_element_by_name("username")
        password = self.driver.find_element_by_name("password")
        username.clear()
        username.send_keys(self.operator_credentials['PHAME_OPERATOR_USERNAME'])
        password.send_keys(self.operator_credentials['PHAME_OPERATOR_PASSWORD'])

        self.driver.find_element_by_name("submitbutton").click()
