"""Main application package."""
import logging
import sys

from celery import Celery
from environs import Env
from flask import Flask
from flask_caching import Cache
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config

env = Env()
env.read_env()

db = SQLAlchemy()
migrate = Migrate(directory="migrations")
cache = Cache()
mail = Mail()
celery = Celery()
jwt = JWTManager()

def create_app(config_object=Config):
    """Create a Flask app."""

    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)

    cache.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    jwt.init_app(app)
    CORS(app)

    from aggrep.api.views import api as api_bp

    app.register_blueprint(api_bp)

    from aggrep.commands import test, lint, seed, collect, pipeline, process, relate, purge

    app.cli.add_command(test)
    app.cli.add_command(lint)
    app.cli.add_command(seed)
    app.cli.add_command(collect)
    app.cli.add_command(process)
    app.cli.add_command(relate)
    app.cli.add_command(purge)
    app.cli.add_command(pipeline)

    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)

    return app
