# from database import Base
# from sqlalchemy import Column, Integer, String
# from sqlalchemy.types import DateTime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return '<User {}>'.format(self.username)
#
# class Signups(Base):
#     """
#     Example Signups table
#     """
#     __tablename__ = 'signups'
#     id = Column(Integer, primary_key=True)
#     name = Column(String(256))
#     email = Column(String(256), unique=True)
#     date_signed_up = Column(DateTime())
#
# class User(Base):
#     __tablename__ = 'user'
#     id = db.Column(Integer, primary_key=True)
#     username = Column(String(64), index=True, unique=True)
#     email = Column(String(120), index=True, unique=True)
#     password_hash = Column(String(128))
#
#     def __repr__(self):
#         return '<User {}>'.format(self.username)
#
#     def set_password(self, password):
#         self.password_hash = generate_password_hash(password)
#
#     def check_password(self, password):
#         return check_password_hash(self.password_hash, password)
