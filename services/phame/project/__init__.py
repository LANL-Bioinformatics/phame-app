import os

from flask import Flask  # new
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_debugtoolbar import DebugToolbarExtension
from flask_cors import CORS

# instantiate the db
db = SQLAlchemy()
login_manager = LoginManager()
toolbar = DebugToolbarExtension()
cors = CORS()


def create_app(script_info=None):

    # instantiate the app
    app = Flask(__name__)

    # set config
    app_settings = os.getenv('APP_SETTINGS')
    app.config.from_object(app_settings)

    # set up extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'phame.login'
    toolbar.init_app(app)
    cors.init_app(app)

    # register blueprints
    from project.api.phame import phame_blueprint
    from project.api.users import users_blueprint
    app.register_blueprint(phame_blueprint, url_prefix='/phame')
    app.register_blueprint(users_blueprint, url_prefix='/users')

    # shell context for flask cli
    @app.shell_context_processor
    def ctx():
        return {'app': app, 'db': db}

    return app


from project.api.models import User


@login_manager.user_loader
def load_user(user_id):
    """Load the logged in user for the LoginManager."""
    return User.query.filter(User.id == int(user_id)).first()
