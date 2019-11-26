"""Defines fixtures available to all tests."""
import logging

import pytest

from aggrep import create_app
from aggrep import db as _db
from config import TestingConfig
from tests.factories import (
    CategoryFactory,
    FeedFactory,
    PostFactory,
    SourceFactory,
    UserFactory,
)


@pytest.fixture
def app():
    """Create application for the tests."""
    _app = create_app(TestingConfig)
    _app.logger.setLevel(logging.CRITICAL)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.yield_fixture(scope="function")
def db(app):
    """Build a test db fixture."""

    _db.app = app
    with app.app_context():
        _db.session.remove()
        _db.drop_all()
        _db.create_all()

    yield _db

    # Explicitly close DB connection
    _db.session.close()
    _db.drop_all()


@pytest.fixture
def category(db):
    """Create a category fixture."""
    instance = CategoryFactory()
    instance.save()
    return instance


@pytest.fixture
def source(db):
    """Create a source fixture."""
    instance = SourceFactory()
    instance.save()
    return instance


@pytest.fixture
def feed(db):
    """Create a feed fixture."""
    instance = FeedFactory()
    instance.save()
    return instance


@pytest.fixture
def post(db):
    """Create a post fixture."""
    instance = PostFactory()
    instance.save()
    return instance


@pytest.fixture
def user(db):
    """Create a user fixture."""
    instance = UserFactory()
    instance.set_password("foobar")
    instance.save()
    return instance
