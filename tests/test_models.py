"""Model unit tests."""
import datetime as dt

import pytest
from sqlalchemy.exc import IntegrityError

from aggrep.models import (
    Category,
    EntityProcessQueue,
    Feed,
    Post,
    SimilarityProcessQueue,
    Source,
    Status,
    User,
)
from aggrep.utils import decode_token


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


@pytest.mark.usefixtures("db")
class TestFeed:
    """Feed Tests."""

    def test_model_create(self, source, category):
        """Create a feed."""
        instance = Feed.create(source=source, category=category, url="foobar.com")
        assert instance.source_id == source.id
        assert instance.category_id == category.id
        assert instance.url == "foobar.com"


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

        assert instance.clicks == []
        assert instance.similar_count == 0
        assert instance.bookmark_count == 0

    def test_title_required(self, feed):
        """Ensure titles are required."""
        with pytest.raises(IntegrityError):
            Post.create(feed=feed, desc="Foo Bar.", link="foobar.com")

    def test_link_required(self, feed):
        """Ensure links are required."""
        with pytest.raises(IntegrityError):
            Post.create(feed=feed, title="foo bar", desc="Foo Bar.")


@pytest.mark.usefixtures("db")
class TestEntityProcessQueue:
    """Entity Queue Tests."""

    def test_model_create(self, post):
        """Ensure model is created with relation."""
        instance = EntityProcessQueue.create(post=post)
        assert instance.post_id == post.id


@pytest.mark.usefixtures("db")
class TestSimilarityProcessQueue:
    """Similarity Queue Tests."""

    def test_model_create(self, post):
        """Ensure model is created with relation."""
        instance = SimilarityProcessQueue.create(post=post)
        assert instance.post_id == post.id


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

    def test_reset_password_token(self, app):
        """Get/Set Reset Password token."""
        user = User.create(email="foo@bar.com")
        key = "reset_password"
        with app.app_context():
            token = user.get_reset_password_token()
            decoded_id = decode_token(key, app.config["SECRET_KEY"], token)
            decoded_user = User.verify_reset_password_token(token)
        assert decoded_id == user.id
        assert decoded_user.id == user.id

    def test_email_confirmation_token(self, app):
        """Get/Set email confirmation token."""
        user = User.create(email="foo@bar.com")
        with app.app_context():
            token = user.get_email_confirm_token()
            decoded_id = decode_token("email_confirm", app.config["SECRET_KEY"], token)
            decoded_user = User.verify_email_confirm_token(token)
        assert decoded_id == user.id
        assert decoded_user.id == user.id
