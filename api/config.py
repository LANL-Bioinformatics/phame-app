import os

basedir = os.path.dirname(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    PROJECT_DIRECTORY = os.path.join(basedir, 'phame_api', 'media')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgres:///phame_api01'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STATIC_FOLDER = '/static/media'
    UPLOAD_DIR = 'static/uploads'
    PHAME_UPLOAD_DIR = '/api/static/uploads'
    MAX_CONTENT_LENGTH = 1000 * 1024 * 1024


