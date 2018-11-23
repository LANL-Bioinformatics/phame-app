import os

basedir = os.path.dirname(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    PROJECT_DIRECTORY = os.path.join(basedir, 'phame_api', 'media')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgres:///phame_api01'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STATIC_FOLDER = '/static/media'
    MAX_CONTENT_LENGTH = 1000 * 1024 * 1024
    POOL_SIZE = 10

