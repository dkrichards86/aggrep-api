"""Post collection unit tests."""
from datetime import date, timedelta
from random import randint
from unittest import TestCase

import pytest

from aggrep.jobs.collect import Collector, PostParser
from aggrep.models import Category, Feed, Source, Status
from aggrep.utils import now
from tests.factories import PostFactory


class FauxFeed:
    """Fake RSS feed."""

    def __init__(self, opts):
        """Make a fake feed."""
        if "title" in opts:
            self.title = opts["title"]
        if "link" in opts:
            self.link = opts["link"]
        if "description" in opts:
            self.description = opts["description"]
        if "summary" in opts:
            self.summary = opts["summary"]
        if "datetime" in opts:
            self.published_parsed = opts["datetime"]


class TestPostParser(TestCase):
    """Test the post parser."""

    def setUp(self):
        """Set up the tests."""
        rss_data = dict(
            title="Aggregate Report",
            link="http://localhost.com",
            description="A description",
            datetime=(2018, 5, 5, 12, 0, 0, 6, 250, 0),
        )
        atom_data = dict(
            title="Aggregate Report",
            link="http://localhost.com",
            summary="A description",
            datetime=(2018, 5, 5, 12, 0, 0, 6, 250, 0),
        )
        self._rss = PostParser(FauxFeed(rss_data))
        self._atom = PostParser(FauxFeed(atom_data))

    def test_datetime(self):
        """Test the datetime attribute."""
        assert self._rss.datetime.date() == date(2018, 5, 5)
        assert self._atom.datetime.date() == date(2018, 5, 5)

        with pytest.raises(AttributeError):
            PostParser(
                FauxFeed(
                    {
                        "title": "Aggregate Report",
                        "link": "http://localhost.com",
                        "description": "A description     ",
                    }
                )
            )

        with pytest.raises(AttributeError):
            PostParser(
                FauxFeed(
                    {
                        "title": "Aggregate Report",
                        "link": "http://localhost.com",
                        "description": "A description     ",
                        "datetime": (2018, 5, 5, 12),
                    }
                )
            )

    def test_description(self):
        """Test the description attribute."""
        expected = "A description"
        assert self._rss.description == expected
        assert self._atom.description == expected

        _desc_markup = PostParser(
            FauxFeed(
                {
                    "title": "Aggregate Report",
                    "link": "http://localhost.com",
                    "datetime": (2018, 5, 5, 12, 0, 0, 6, 250, 0),
                    "description": "A description <br/>",
                }
            )
        )
        assert _desc_markup.description == expected

        _no_desc = PostParser(
            FauxFeed(
                {
                    "title": "Aggregate Report",
                    "link": "http://localhost.com",
                    "datetime": (2018, 5, 5, 12, 0, 0, 6, 250, 0),
                }
            )
        )
        assert _no_desc.description == ""

    def test_link(self):
        """Test the link attribute."""
        expected = "http://localhost.com"
        assert self._rss.link == expected
        assert self._atom.link == expected

        with pytest.raises(AttributeError):
            PostParser(
                FauxFeed(
                    {
                        "title": "Aggregate Report",
                        "description": "A description     ",
                        "datetime": (2018, 5, 5, 12, 0, 0, 6, 250, 0),
                    }
                )
            )

    def test_title(self):
        """Test the title attribute."""
        expected = "Aggregate Report"
        assert self._rss.title == expected
        assert self._atom.title == expected

        with pytest.raises(AttributeError):
            PostParser(
                FauxFeed(
                    {
                        "link": "http://localhost.com",
                        "description": "A description     ",
                        "datetime": (2018, 5, 5, 12, 0, 0, 6, 250, 0),
                    }
                )
            )


@pytest.mark.usefixtures("db")
class TestCollect:
    """Collection module tests."""

    def test_due_feeds(self):
        """Test fetching due feeds."""

        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")

        due = 0
        for i in range(8):
            freq = randint(3, 8)
            rand = randint(1, 3)

            offset = now() - timedelta(minutes=(2 ** (freq - 1)))
            if rand > 1:
                offset = now() - timedelta(minutes=(2 ** freq))
                due += 1

            feed = Feed.create(source=src, category=cat, url="{}.feed.com".format(i))
            Status.create(
                feed_id=feed.id, update_datetime=offset, update_frequency=freq
            )

        collector = Collector()
        collector.get_due_feeds()
        assert len(collector.due_feeds) == due

    def test_get_source_posts(self):
        """Test getting posts from a particular source."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        collector = Collector()
        posts = collector.get_source_posts(src)
        assert type(posts) == set
        assert len(posts) == 5
