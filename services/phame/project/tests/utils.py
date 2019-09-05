import json
from flask import url_for
from project.api.models import User
from project import db


def add_user(username, email, password, is_admin=False):
    user = User(username=username, email=email, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login_user(client):
    resp_login = client.post(url_for('auth.login_user'),
                             data=json.dumps(
                                 {'email': 'test@test.com',
                                  'password': 'test'}),
                             content_type='application/json')
