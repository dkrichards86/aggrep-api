"""Settings module for test app."""
TESTING = True
ENV = "development"
SECRET_KEY = "not-so-secret-in-tests"
BCRYPT_LOG_ROUNDS = 4

CACHE_TYPE = "simple"

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = "sqlite://"
MAIL_DEFAULT_SENDER = "foo@bar.com"
WTF_CSRF_ENABLED = False
