"""Model unit tests."""
import datetime as dt

import pytest
from sqlalchemy.exc import IntegrityError

from aggrep.models import Category, Feed, Post, Source, Status, User
from aggrep.utils import decode_token, encode_token
from tests.factories import PostFactory


@pytest.mark.usefixtures("db")
class TestPKMixin:
    """Primary key mixin tests."""

    def test_model_create(self):
        """Check a model for an ID column."""
        instance = Category.create(slug="slug", title="title")
        assert instance.id == 1


@pytest.mark.usefixtures("db")
class TestCRUDMixin:
    """CRUD mixin tests."""

    def test_model_create(self):
        """Create a model."""
        instance = Category.create(slug="slug", title="title")
        assert instance.id == 1

    def test_model_update(self):
        """Update a model."""
        instance = Category.create(slug="slug", title="title")
        assert instance.slug == "slug"
        assert Category.query.filter(Category.slug == "slug2").count() == 0

        instance.update(slug="slug2")
        assert instance.slug == "slug2"

        assert Category.query.filter(Category.slug == "slug2").count() == 1

    def test_model_save(self):
        """Save a model."""
        instance = Category.create(slug="slug", title="title")
        assert instance.slug == "slug"
        assert Category.query.filter(Category.slug == "slug2").count() == 0

        instance.slug = "slug2"
        instance.save()

        assert Category.query.filter(Category.slug == "slug2").count() == 1

    def test_model_delete(self):
        """Delete a model."""
        Category.create(slug="slug", title="title")
        Category.create(slug="slug2", title="title2")
        assert Category.query.count() == 2

        c = Category.query.get(1)
        c.delete()

        assert Category.query.count() == 1


@pytest.mark.usefixtures("db")
class TestCategory:
    """Category Tests."""

    def test_model_create(self):
        """Create an category."""
        instance = Category.create(slug="slug", title="title")
        assert instance.slug == "slug"
        assert instance.title == "title"

    def test_slug_uniqueness(self, category):
        """Test unique constraints on keys."""
        with pytest.raises(IntegrityError):
            Category.create(slug=category.slug, title="title")

    def test_title_uniqueness(self, category):
        """Test unique constraints on keys."""
        with pytest.raises(IntegrityError):
            Category.create(slug="slug", title=category.title)

    def test_repr(self):
        """Test string representation."""
        instance = Category.create(slug="slug", title="title")
        assert str(instance) == "title"

    def test_to_dict(self):
        """Write a category to a dict."""
        instance = Category.create(slug="slug", title="title")

        as_dict = instance.to_dict()
        assert as_dict["slug"] == "slug"
        assert as_dict["title"] == "title"


@pytest.mark.usefixtures("db")
class TestSource:
    """Source Tests."""

    def test_model_create(self):
        """Create an category."""
        instance = Source.create(slug="slug", title="title")
        assert instance.slug == "slug"
        assert instance.title == "title"

    def test_slug_uniqueness(self, source):
        """Test unique constraints on keys."""
        with pytest.raises(IntegrityError):
            Source.create(slug=source.slug, title="title")

    def test_repr(self):
        """Test string representation."""
        instance = Source.create(slug="slug", title="title")
        assert str(instance) == "title"

    def test_to_dict(self):
        """Write a source to a dict."""
        instance = Source.create(slug="slug", title="title")
        as_dict = instance.to_dict()
        assert as_dict["slug"] == "slug"
        assert as_dict["title"] == "title"


@pytest.mark.usefixtures("db")
class TestFeed:
    """Feed Tests."""

    def test_model_create(self, source, category):
        """Create a feed."""
        instance = Feed.create(source=source, category=category, url="foobar.com")
        assert instance.source_id == source.id
        assert instance.category_id == category.id
        assert instance.url == "foobar.com"

    def test_to_dict(self):
        """Write a feed to a dict."""
        cat = Category.create(slug="cat", title="cat title")
        src = Source.create(slug="src", title="src title")
        instance = Feed.create(source=src, category=cat, url="foobar.com")

        expected = dict(source=src.to_dict(), category=cat.to_dict(), url="foobar.com")

        assert instance.to_dict() == expected


@pytest.mark.usefixtures("db")
class TestStatus:
    """Feed Status Tests."""

    def test_model_create(self, feed):
        """Create an category."""
        instance = Status.create(feed=feed)
        assert instance.feed_id == feed.id
        assert instance.update_frequency == 0
        assert bool(instance.update_datetime)
        assert isinstance(instance.update_datetime, dt.datetime)
        assert instance.feed.url == feed.url


@pytest.mark.usefixtures("db")
class TestPost:
    """Post Tests."""

    def test_model_create(self, feed):
        """Create a post."""
        instance = Post.create(
            feed=feed, title="foo bar", desc="Foo Bar.", link="foobar.com"
        )
        assert instance.title == "foo bar"
        assert instance.desc == "Foo Bar."
        assert instance.link == "foobar.com"
        assert instance.feed_id == feed.id
        assert bool(instance.published_datetime)
        assert isinstance(instance.published_datetime, dt.datetime)
        assert bool(instance.ingested_datetime)
        assert isinstance(instance.ingested_datetime, dt.datetime)

    def test_title_required(self, feed):
        """Ensure titles are required."""
        with pytest.raises(IntegrityError):
            Post.create(feed=feed, desc="Foo Bar.", link="foobar.com")

    def test_link_required(self, feed):
        """Ensure links are required."""
        with pytest.raises(IntegrityError):
            Post.create(feed=feed, title="foo bar", desc="Foo Bar.")

    def test_repr(self, feed):
        """Test string representation."""
        instance = Post.create(
            feed=feed, title="foo bar", desc="Foo Bar.", link="foobar.com"
        )
        assert str(instance) == "1: foo bar"

    def test_pagination(self):
        """Test post pagination."""

        for instance in PostFactory.create_batch(25):
            instance.save()

        pagination = Post.to_collection_dict(Post.query, 1, 20)

        assert len(pagination["items"]) == 20
        assert pagination["page"] == 1
        assert pagination["per_page"] == 20
        assert pagination["total_pages"] == 2
        assert pagination["total_items"] == 25

    def test_uid(self, post):
        """Test post UIDs."""

        assert Post.from_uid(post.uid) == post


@pytest.mark.usefixtures("db")
class TestUsers:
    """User tests."""

    def test_model_create(self):
        """Test creation data."""
        user = User.create(email="foo@bar.com")
        assert user.email == "foo@bar.com"
        assert user.password is None
        assert user.confirmed is False
        assert user.active is True

    def test_uniqueness(self):
        """Test unique constraints on keys."""
        User.create(email="foo@bar.com")

        with pytest.raises(IntegrityError):
            User.create(email="foo@bar.com")

    def test_password_is_nullable(self):
        """Test null password."""
        user = User.create(email="foo@bar.com")
        assert user.password is None

    def test_password(self):
        """Check password."""
        user = User.create(email="foo@bar.com")
        user.set_password("foobarbaz123")
        assert user.check_password("foobarbaz123") is True
        assert user.check_password("barfoobaz") is False

    def test_verify_reset_password_token(self, app):
        """Get/Set Reset Password token."""
        user = User.create(email="foo@bar.com")
        key = "reset_password"
        with app.app_context():
            token = user.get_reset_password_token()
            decoded_id = decode_token(key, app.config["SECRET_KEY"], token)
            decoded_user = User.verify_reset_password_token(token)
        assert decoded_id == user.id
        assert decoded_user.id == user.id

    def test_verify_reset_password_token_none(self, app):
        """Test 'None' reset password token."""
        with app.app_context():
            token = encode_token(
                "reset_password", None, app.config["SECRET_KEY"], expires_in=60
            )
            decoded_user = User.verify_reset_password_token(token)

        assert decoded_user is None

    def test_email_confirmation_token(self, app):
        """Get/Set email confirmation token."""
        user = User.create(email="foo@bar.com")
        with app.app_context():
            token = user.get_email_confirm_token()
            decoded_id = decode_token("email_confirm", app.config["SECRET_KEY"], token)
            decoded_user = User.verify_email_confirm_token(token)
        assert decoded_id == user.id
        assert decoded_user.id == user.id

    def test_verify_email_confirm_token_none(self, app):
        """Test 'None' email confirmation token."""
        with app.app_context():
            token = encode_token(
                "email_confirm", None, app.config["SECRET_KEY"], expires_in=60
            )
            decoded_user = User.verify_email_confirm_token(token)

        assert decoded_user is None

    def test_to_dict(self, user):
        """Test user as a dict."""
        assert user.to_dict() == dict(email=user.email, confirmed=user.confirmed)

    def test_repr(self, user):
        """Test string representation."""
        assert str(user) == user.email

    def test_get_user_from_identity(self, user):
        """Test pull a user from JWT identity."""

        instance = User.get_user_from_identity(user.email)

        assert instance.id == user.id
        assert instance.email == user.email

    def test_get_user_from_identity_none(self):
        """Test pull a user from invalid JWT identity."""

        instance = User.get_user_from_identity("foo@bar.com")

        assert instance is None
