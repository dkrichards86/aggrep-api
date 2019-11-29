"""Application configuration."""
from datetime import timedelta

from environs import Env

env = Env()
env.read_env()


class Config:
    """Base app configs."""

    DEBUG = False
    TESTING = False
    LOG_LEVEL = "info"

    SECRET_KEY = env.str("SECRET_KEY", "")
    BCRYPT_LOG_ROUNDS = 13

    SQLALCHEMY_DATABASE_URI = env.str("DATABASE_URL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    _CACHE_HOST = env.str("REDIS_URL", "")
    _CACHE_DB = 0
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = "{}/{}".format(_CACHE_HOST, _CACHE_DB)

    _CELERY_HOST = env.str("REDIS_URL", "")
    _CELERY_DB = 1
    _CELERY_URL = "{}/{}".format(_CELERY_HOST, _CELERY_DB)
    CELERY_BROKER_URL = _CELERY_URL
    CELERY_RESULT_BACKEND = _CELERY_URL

    SENDGRID_DEFAULT_FROM = env.str("SENDGRID_DEFAULT_FROM", "")
    SENDGRID_API_KEY = env.str("SENDGRID_API_KEY", "")

    WTF_CSRF_ENABLED = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=14)
    UI_URL = env.str("UI_URL", "")


class ProductionConfig(Config):
    """Prod app configs."""

    pass


class DevelopmentConfig(Config):
    """Dev app configs."""

    DEBUG = True
    LOG_LEVEL = "debug"


class TestingConfig(Config):
    """Testing app configs."""

    TESTING = True
    DEBUG = True
    LOG_LEVEL = "debug"
    SECRET_KEY = "not-so-secret-in-tests"
    SQLALCHEMY_DATABASE_URI = "sqlite://"

    BCRYPT_LOG_ROUNDS = 4
    CACHE_TYPE = "null"
