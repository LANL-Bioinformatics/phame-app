# services/phame/project/config.py

import os
basedir = os.path.dirname(os.path.dirname(__file__))


class BaseConfig:
    """Base configuration"""
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG_TB_ENABLED = False
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    MAX_CONTENT_LENGTH = 1000 * 1024 * 1024
    PROJECT_DIRECTORY = os.path.join('/phame_api', 'media')
    UPLOAD_DIRECTORY = os.path.join('static', 'uploads')
    PHAME_UPLOAD_DIR = os.path.join('/usr', 'src', 'app', 'static', 'uploads')
    PUBLIC_PROJECTS_DIR = os.path.join('/usr', 'src', 'app', 'project', 'api', 'public')
    SEND_NOTIFICATIONS = False


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')  # new
    DEBUG_TB_ENABLED = True


class TestingConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_TEST_URL')
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True
    DEBUG = True
    PROJECT_DIRECTORY = os.path.join('/test', 'media')
    UPLOAD_DIRECTORY = os.path.join('/test', 'static', 'uploads')
    PHAME_UPLOAD_DIR = os.path.join('/test', 'static', 'uploads')


class ProductionConfig(BaseConfig):
    """Production configuration"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SEND_NOTIFICATIONS = True
