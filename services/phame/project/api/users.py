import os
import requests
import zipfile
import shutil
from tempfile import mkstemp
import logging
import json
import re
import pandas as pd
from uuid import uuid4
import celery.states as states
import ast
from sqlalchemy.exc import IntegrityError, DataError, TimeoutError
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, send_file, current_app

from werkzeug.urls import url_parse
from flask_login import current_user, login_user, logout_user, login_required
from project import db
from project.api.models import User
from project.api.forms import LoginForm, InputForm, SignupForm, RegistrationForm, SubsetForm, AdminForm


users_blueprint = Blueprint('users', __name__, template_folder='templates', static_folder='static')


@users_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login for PhaME
    If user is logged in as 'public', they are redirected to the 'projects' page where they
    can view 'public' projects
    :return:
    """
    # if current_user.is_authenticated:
    #     return redirect(url_for('phame.projects')) if current_user.username == 'public' else redirect(url_for('phame.index'))
    form = LoginForm()
    if form.validate_on_submit():
        if not form.public_login.data:
            user = User.query.filter_by(username=form.username.data).first()
            if user is None or not user.check_password(form.password.data):
                flash('Invalid username or password')
                return redirect(url_for('users.login'))
        else:
            user = User.query.filter_by(username='public').first()
        logging.debug(f'user {user.username}')

        logging.debug(f"request next page {request.args.get('next')}")
        login_user(user, remember=form.remember_me.data)
        next_page = url_for('phame.projects') if current_user.username == 'public' else request.args.get('next')
        logging.debug(f'next page {next_page}')
        if not next_page or url_parse(next_page).netloc != '':
            # url_for returns /input

            next_page = 'phame.' + url_for('phame.projects') if current_user.username == 'public' else 'phame.' + url_for('phame.input').split('/')[-1]
            logging.debug(f'not next page {next_page}')
        logging.debug(f"next_page split {'.'.join(next_page.split('/')[-2:])}")
        # logging.debug(f"next_page split {'phame.' + url_for(next_page.split('/')[-1])}")
        return redirect(url_for('.'.join(next_page.split('/')[-2:])))
    return render_template('login.html', title='Sign In', form=form)


@users_blueprint.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('users.login'))


@users_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registration for PhaME
    :return:
    """
    if current_user.is_authenticated:
        return redirect(url_for('users.index'))
    form = RegistrationForm()
    logging.debug(f'form {form.__dict__}')
    logging.debug(f'username {form.username.data}')
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        logging.debug(f'user {user}')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        logging.debug(f"project directory {current_app.config['PROJECT_DIRECTORY']}")
        if not os.path.exists(os.path.join(current_app.config['PROJECT_DIRECTORY'], user.username)):
            os.makedirs(os.path.join(current_app.config['PROJECT_DIRECTORY'], user.username))
        if not os.path.exists(os.path.join(current_app.config['UPLOAD_DIRECTORY'], user.username)):
            os.makedirs(os.path.join(current_app.config['UPLOAD_DIRECTORY'], user.username))
        return redirect(url_for('users.login'))
    return render_template('register.html', title='Register', form=form)


@users_blueprint.route('/users', methods=['POST'])
def add_user():
    post_data = request.get_json()
    response_object = {
        'status': 'fail',
        'message': 'Invalid payload'
    }
    if not post_data:
        return jsonify(response_object), 400
    username = post_data.get('username')
    email = post_data.get('email')
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            db.session.add(User(username=username, email=email))
            db.session.commit()
            response_object = {
                'status': 'success',
                'message': f'{email} was added!'
            }
            return jsonify(response_object), 201
        else:
            response_object['message'] = 'Sorry. That email already exists.'
            return jsonify(response_object), 400
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(response_object), 400


@users_blueprint.route('/profile', methods=['GET', 'POST'])
def profile():
    if current_user.username == 'admin':
        form = AdminForm()
        user_list = User.query.all()
        for a in user_list:
            logging.debug(a.username)
        # form.manage_username.choices = [(a.username, a.username) for a in user_list]
        if request.method == 'POST':
            return redirect(url_for('phame.projects', username=form.manage_username.data))
        return render_template('admin.html', user=current_user, form=form)
    else:
        return render_template('profile.html', user=current_user)



@users_blueprint.route('/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': 'success',
        'message': 'pong!'
    })



@users_blueprint.route('/users/<user_id>', methods=['GET'])
def get_single_user(user_id):
    """Get single user details"""
    response_object = {
        'status': 'fail',
        'message': 'User does not exist'
    }
    try:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify(response_object), 404
        else:
            response_object = {
                'status': 'success',
                'data': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'active': user.active
                }
            }
        return jsonify(response_object), 200
    except ValueError:
        return jsonify(response_object), 404
    except DataError:
        return jsonify(response_object), 404


@users_blueprint.route('/users', methods=['GET'])
def get_all_users():
    """Get all users"""
    response_object = {
        'status': 'success',
        'data': {
            'users': [user.to_json() for user in User.query.all()]
        }
    }
    return jsonify(response_object), 200
