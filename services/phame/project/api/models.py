# services/phame/project/api/models.py


from flask_login import UserMixin
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

from project import db
# from project.api.phame import convert_seconds_to_time


class User(db.Model, UserMixin):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128))
    active = db.Column(db.Boolean(), default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=func.now(), nullable=False)
    projects = db.relationship('Project', backref='user', lazy=True)

    # def __init__(self, username, email, password_hash):
    #     self.username = username
    #     self.email = email
    #     self.password_hash = password_hash

    def to_json(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'active': self.active
        }

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Project(db.Model):

    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    execution_time = db.Column(db.Integer)
    status = db.Column(db.String(30))
    num_threads = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def convert_seconds_to_time(self):
        m, s = divmod(self.execution_time, 60)
        h, m = divmod(m, 60)
        exec_time_string = "%d:%02d:%02d" % (h, m, s)
        return exec_time_string

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'start_time': self.start_time,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'execution_time': self.convert_seconds_to_time(),
            'num_threads': self.num_threads
        }
