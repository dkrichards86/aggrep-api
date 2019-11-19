"""Application configuration."""
from datetime import timedelta

from environs import Env

env = Env()
env.read_env()


class Config:
    """Configuration object for the application."""

    ENV = env.str("FLASK_ENV", default="production")
    DEBUG = ENV == "development"
    LOG_LEVEL = "info" if ENV == "production" else "debug"

    SECRET_KEY = env.str("SECRET_KEY")
    BCRYPT_LOG_ROUNDS = 13

    SQLALCHEMY_DATABASE_URI = env.str("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    _CACHE_HOST = env.str("REDIS_URL")
    _CACHE_DB = 0
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = "{}/{}".format(_CACHE_HOST, _CACHE_DB)

    _CELERY_HOST = env.str("REDIS_URL")
    _CELERY_DB = 1
    _CELERY_URL = "{}/{}".format(_CELERY_HOST, _CELERY_DB)
    CELERY_BROKER_URL = _CELERY_URL
    CELERY_RESULT_BACKEND = _CELERY_URL

    MAIL_SERVER = env.str("MAIL_SERVER")
    MAIL_PORT = env.str("MAIL_PORT")
    MAIL_USE_TLS = env.str("MAIL_USE_TLS")
    MAIL_DEFAULT_SENDER = env.str("MAIL_DEFAULT_SENDER")
    MAIL_USERNAME = env.str("MAIL_USERNAME")
    MAIL_PASSWORD = env.str("MAIL_PASSWORD")

    WTF_CSRF_ENABLED = False

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=14)
