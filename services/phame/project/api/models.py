# services/phame/project/api/models.py
from datetime import datetime
import enum
from flask_login import UserMixin
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

from project import db
# from project.api.phame import convert_seconds_to_time

class IntEnum(db.TypeDecorator):
    """
    Enables passing in a Python enum and storing the enum's *value* in the db.
    The default would have stored the enum's *name* (ie the string).
    """
    impl = db.Integer

    def __init__(self, enumtype, *args, **kwargs):
        super(IntEnum, self).__init__(*args, **kwargs)
        self._enumtype = enumtype

    def process_bind_param(self, value, dialect):
        if isinstance(value, int):
            return value

        return value.value

    def process_result_value(self, value, dialect):
        return self._enumtype(value)

class StatusTypes(enum.IntEnum):
    PROGRESS = 1
    SUCCESS = 2
    FAILURE = 3

class User(db.Model, UserMixin):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    active = db.Column(db.Boolean(), default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=func.now(), nullable=False)
    is_admin = db.Column(db.Boolean(), default=False, nullable=False)
    projects = db.relationship('Project', backref='user', lazy=True)

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
    start_time = db.Column(db.DateTime, default=datetime.now())
    end_time = db.Column(db.DateTime, default=datetime.now())
    execution_time = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default='PENDING')
    # status = db.Column(IntEnum(StatusTypes), default=StatusTypes.FAILURE)
    num_threads = db.Column(db.Integer, default=2)
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
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'execution_time': self.convert_seconds_to_time(),
            'num_threads': self.num_threads
        }
