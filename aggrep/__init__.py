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


def register_app(config_object):
    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)

    return app


def register_extensions(app):
    cache.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    jwt.init_app(app)
    CORS(app)


def register_blueprints(app):
    from aggrep.api.views import api as api_bp
    from aggrep.api.views import app as app_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(app_bp)


def register_commands(app):
    from aggrep.commands import (
        test, lint, seed, collect, pipeline, process, relate, purge, updatestats,
    )

    app.cli.add_command(test)
    app.cli.add_command(lint)
    app.cli.add_command(seed)
    app.cli.add_command(collect)
    app.cli.add_command(process)
    app.cli.add_command(relate)
    app.cli.add_command(purge)
    app.cli.add_command(pipeline)
    app.cli.add_command(updatestats)


def register_logger(app):
    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)


def create_app(config_object=Config):

    app = register_app(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_commands(app)
    register_logger(app)

    return app
