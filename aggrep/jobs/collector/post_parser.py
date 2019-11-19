"""Post parsing module."""
from datetime import datetime
from time import mktime

from bs4 import BeautifulSoup


class PostParser:
    """PostParser accepts a `feedparser` post object and normalizes it for ingestion.

    See: https://pythonhosted.org/feedparser/index.html
    """

    def __init__(self, post):
        """Initialize the post parser."""
        self.post = post

        self.title = self.get_title()
        self.link = self.get_link()
        self.description = self.get_description()
        self.datetime = self.get_datetime()

    def get_datetime(self):
        """Get a datetime from the post.

        If the post doesn't exist, use the current datetime.
        """
        if hasattr(self.post, "published_parsed"):
            try:
                return datetime.fromtimestamp(mktime(self.post.published_parsed))
            except TypeError:
                raise AttributeError("Unable to parse datetime")
        else:
            raise AttributeError("No pubished datetime provided")

    def get_description(self):
        """Pull a description from the feed.

        In the case of RSS feeds, this is accessible in the 'description' attribute. In Atom feeds,
        this is pulled from the 'summary' attribute. Once we have a description, use BeautifulSoup
        to strip markup, leaving raw text. Finally, strip all trailing whitespace.
        """
        if hasattr(self.post, "description") and self.post.description:
            # RSS feed
            return BeautifulSoup(self.post.description, "lxml").get_text(
                " ", strip=True
            )
        elif hasattr(self.post, "summary") and self.post.summary:
            # Atom feed
            return BeautifulSoup(self.post.summary, "lxml").get_text(" ", strip=True)
        else:
            return ""

    def get_link(self):
        """Treat post link as an attribute."""
        if hasattr(self.post, "link") and self.post.link:
            return self.post.link
        else:
            raise AttributeError

    def get_title(self):
        """Treat post title as an attribute."""
        if hasattr(self.post, "title") and self.post.title:
            return self.post.title
        else:
            raise AttributeError
