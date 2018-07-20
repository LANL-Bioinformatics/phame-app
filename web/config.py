import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    PROJECT_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'phame_api01', 'phame_api01', 'media')
