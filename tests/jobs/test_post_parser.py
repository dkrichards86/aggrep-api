"""Test post parsing module."""
from datetime import date
from unittest import TestCase

import pytest

from aggrep.jobs.collector.post_parser import PostParser


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
