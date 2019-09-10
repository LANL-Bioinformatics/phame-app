import os
import logging
from sqlalchemy.exc import IntegrityError, DataError
from flask import Blueprint, jsonify, request, render_template, \
    redirect, url_for, flash, current_app

from werkzeug.urls import url_parse
from flask_login import current_user, login_user, logout_user
from project import db
from project.api.models import User, Project
from project.api.forms import LoginForm, RegistrationForm, AdminForm, DeleteUserForm


users_blueprint = Blueprint('users', __name__, template_folder='templates',
                            static_folder='static')

@users_blueprint.route('/api/login', methods=['POST'])
def api_login():
    response_object = {'status': 'fail', 'message': 'Invalid payload'}
    try:
        logging.debug('api_login')
        post_data = request.json
        logging.debug(f'post_data {post_data}')
        logging.debug(f"username {post_data['username']}")
        logging.debug(f"password {post_data['password']}")
        if not post_data:
            return jsonify(response_object), 400
        username = post_data['username']
        password = post_data['password']
        user = User.query.filter_by(username=username).first()
        logging.debug(f'user {user.username}')
        if not user:
            return jsonify(response_object), 404
        if user.check_password(password):
            logging.debug('password checked')
            login_user(user)
            logging.debug('user logged int')
            response_object['message'] = 'Successfully logged in'
            response_object['status'] = 'success'
            return jsonify(response_object), 200
    except ValueError:
        logging.debug('could not login')
        return jsonify(response_object), 404
    except DataError:
        return jsonify(response_object), 404

@users_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login for PhaME
    If user is logged in as 'public', they are redirected to the 'projects'
    page where they
    can view 'public' projects
    :return:
    """
    # if current_user.is_authenticated:
    #     return redirect(url_for('phame.projects')) if
    #     current_user.username == 'public' else
    #     redirect(url_for('phame.index'))
    form = LoginForm()
    if form.validate_on_submit():
        if not form.public_login.data:
            user = User.query.filter_by(username=form.username.data).first()
            if user is None or not user.check_password(form.password.data):
                flash('Invalid username or password')
                return redirect(url_for('users.login'))
        else:
            user = User.query.filter_by(username='public').first()
        # logging.debug(f'logged in user {user.username}')

        # logging.debug(f"request next page {request.args.get('next')}")
        login_user(user, remember=form.remember_me.data)
        next_page = url_for('phame.projects') if \
            current_user.username == 'public' else request.args.get('next')
        # logging.debug(f'next page {next_page}')
        if not next_page or url_parse(next_page).netloc != '':
            # url_for returns /input

            next_page = 'phame.' + url_for('phame.projects') if \
                current_user.username == 'public' else \
                'phame.' + url_for('phame.input').split('/')[-1]
            # logging.debug(f'not next page {next_page}')

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
        # logging.debug('current user is authenticated')
        return redirect(url_for('phame.index'))
    form = RegistrationForm()
    # logging.debug(f'form {form.__dict__}')
    # logging.debug(f'username {form.username.data}')
    response_object = {
        'status': 'fail',
        'message': 'Invalid payload'
    }
    if form.validate_on_submit():
        try:
            # logging.debug(f'form email {form.email.data}')
            user = User.query.filter_by(email=form.email.data).first()
            # logging.debug(f'register user {user}')
            if not user:
                user = User(username=form.username.data,
                            email=form.email.data)
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()

                user = User.query.filter_by(email=form.email.data).first()
                # logging.debug(f'user query {user.email}')
                flash('Congratulations, you are now a registered user!')
                if not os.path.exists(os.path.join(
                        current_app.config['PROJECT_DIRECTORY'],
                        user.username)):
                    os.makedirs(os.path.join(
                        current_app.config['PROJECT_DIRECTORY'],
                        user.username))
                if not os.path.exists(os.path.join(
                        current_app.config['UPLOAD_DIRECTORY'],
                        user.username)):
                    os.makedirs(os.path.join(
                        current_app.config['UPLOAD_DIRECTORY'],
                        user.username))

                response_object = {'status': 'success',
                                   'message': f'{form.email.data} was added'}
                return redirect(url_for('users.login'))
            else:
                # logging.debug(f'response_object {response_object}')
                response_object['message'] = \
                    'Sorry. That email already exists.'
                return jsonify(response_object), 400
        except IntegrityError:
            db.session.rollback()
            return jsonify(response_object), 400

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
        # logging.debug(f'register user {user}')
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
    except IntegrityError:
        db.session.rollback()
        return jsonify(response_object), 400


@users_blueprint.route('/profile', methods=['GET', 'POST'])
def profile():
    logging.debug(f'current_user {current_user.username} is admin {current_user.is_admin}')
    if current_user.is_admin:
        admin_form = AdminForm()
        if request.method == 'POST':
            return redirect(url_for('phame.projects',
                                    username=admin_form.manage_username.data))
        return render_template('admin.html', user=current_user, form=admin_form)
    else:
        return render_template('profile.html', user=current_user)


@users_blueprint.route('/delete', methods=['GET', 'POST'])
def delete():
    logging.debug(f'current_user {current_user.username} is admin {current_user.is_admin}')
    if current_user.is_admin:
        admin_form = DeleteUserForm()
        if request.method == 'POST':

            user = User.query.filter_by(username=admin_form.manage_username.data).first()
            projects = Project.query.filter_by(user=user)
            for project in projects:
                logging.debug(f'project {project}')
                db.session.delete(project)
                db.session.commit()
            logging.debug(f'deleting user {user.username}')
            db.session.delete(user)
            db.session.commit()
            return redirect(url_for('phame.projects',
                                    username=admin_form.manage_username.data))
        return render_template('admin.html', user=current_user, form=admin_form)
    else:
        return render_template('profile.html', user=current_user)

# @users_blueprint.route('/delete', methods=['POST'])
# def delete_user():
#     response_object = {'status': 'fail', 'message': 'Cannot delete user'}
#     logging.debug('delete called')
#     logging.debug(request)
#     logging.debug(f'request.is_json {request.is_json}')
#     post_data = request.get_json()
#     logging.debug(post_data)
#     logging.debug(f'request.get_json() {request.get_json()}')
#     try:
#         if not current_user and current_user.is_admin:
#             response_object['message'] = 'You must be an admin to delete users!'
#             return jsonify(response_object), 422
#
#         if not post_data:
#             return jsonify(response_object), 400
#         username = post_data.get('username')
#         user = User.query.filter_by(username=username).first()
#         logging.debug(f'deleting user {username}')
#         db.session.delete(user)
#         db.session.commit()
#         response_object['message'] = f'Successfully deleted {username}'
#         response_object['status'] = f'success'
#         return jsonify(response_object), 200
#     except IntegrityError as e:
#         logging.debug(f'Error deleting user: {e}')
#         db.session.rollback()
#         return jsonify(response_object), 400
#     except AttributeError as e:
#         logging.debug(f'Error deleting user: {e}')
#         db.session.rollback()
#         return jsonify(response_object), 400
#     except Exception as e:
#         logging.debug(f'Error deleting user: {e}')
#         db.session.rollback()
#         return jsonify(response_object), 400


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


@users_blueprint.route('/users/name/<username>', methods=['GET'])
def get_single_username(username):
    """Get single user details for given username"""
    response_object = {
        'status': 'fail',
        'message': 'User does not exist'
    }
    try:
        user = User.query.filter_by(username=username).first()
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
