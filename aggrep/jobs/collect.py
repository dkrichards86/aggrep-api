"""Post collection job."""
<<<<<<< HEAD
import re
import requests
=======
>>>>>>> master
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser
from bs4 import BeautifulSoup
from flask import current_app

from aggrep import db
from aggrep.jobs.base import Job
from aggrep.models import Feed, Post, PostAction, SimilarityProcessQueue, Source, Status
from aggrep.utils import now

MIN_UPDATE_FREQ = 3  # 2**3 minutes (8)
MAX_UPDATE_FREQ = 7  # 2**7 minutes (128)


class OpenGraphParser:
    def __init__(self, url):
        self.attrs = dict()
        self._url = url
        self.parse()

    def _get(self, attr):
        return self.attrs.get(attr)

    @property
    def url(self):
        return self._get('url')

    @property
    def title(self):
        return self._get('title')

    @property
    def image(self):
        return self._get('image')

    @property
    def description(self):
        return self._get('description')

    def fetch(self):
        headers = {'User-Agent': 'Aggregate Report/1.0'}

        content = requests.get(self._url, headers=headers, timeout=2)
        content.raise_for_status()
        return content.text

    def parse(self):
        content = self.fetch()
        soup = BeautifulSoup(content, "html5lib")

        og_tags = soup.findAll(property=re.compile(r'^og'))
        for tag in og_tags:
            if tag.has_attr('content'):
                self.attrs[tag['property'][3:]] = tag['content']


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
        """Get a datetime from the post."""
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


def process_posts(feed, link_urls, collection_offset):
    """Process posts from a RSS feed."""
    posts = []
    feed_data = feedparser.parse(feed.url)

    # For each entry in the RSS feed, parse the content then update
    # the database. First we create a new post. We then build entities
    # and Feed <-> Post entries.
    for entry in feed_data.entries:
        try:
            post = PostParser(entry)
        except AttributeError:
            # This post was missing critical entries.
            continue

        # If the post has a published datetime, make it TZ aware.
        # Otherwise set the published time to now.
        try:
            post_datetime = post.datetime.astimezone()
        except Exception:
            continue

        # discard entries with irregular dates
        if post_datetime > now() or post_datetime < collection_offset:
            continue

        if len(post.title) > 255 or len(post.link) > 255:
            continue

        if post.link in link_urls:
            continue

        title = post.title
        desc = post.description
        try:
            og = OpenGraphParser(post.link)

            if og.title is not None:
                title = og.title

            if og.description is not None:
                desc = og.description
        except Exception:
            pass

        # If this particular post has not been processed
        # previously, process it.
        link_urls.add(post.link)

        # Build the post object.
        p = Post(
            feed_id=feed.id,
            title=title,
            desc=desc,
            link=post.link,
            published_datetime=post_datetime,
        )
        posts.append(p)

    return posts


class Collector(Job):
    """Post collection job."""

    identifier = "COLLECT"
    lock_timeout = 8

    def __init__(self, ndays=1):
        """Init."""
        super().__init__()
        self._collection_offset = now() - timedelta(days=ndays)
        self._archival_offset = now() - timedelta(days=ndays + 1)

    def get_due_feeds(self):
        """Get feeds in need of processing."""
        due_feeds = []
        for status in Status.query.order_by(Status.id).all():
            update_datetime = status.update_datetime.replace(tzinfo=timezone.utc)

            status_offset = 2 ** status.update_frequency
            if update_datetime <= now() - timedelta(minutes=status_offset):
                due_feeds.append(status.feed)

        self.due_feeds = due_feeds

    def get_source_posts(self, source):
        """Get posts from a source."""
        source_posts = Post.query.filter(
            Post.published_datetime >= self._archival_offset
        ).filter(Post.feed.has(Feed.source.has(Source.id == source.id)))

        return set(post.link for post in source_posts)

    def process_feeds(self):
        """Process feeds ready for review."""
        feed_posts = []
        with ThreadPoolExecutor() as executor:
            futures_to_feed = {}

            for feed in self.due_feeds:
                link_urls = self.get_source_posts(feed.source)
                futures_to_feed[executor.submit(process_posts, feed, link_urls, self._collection_offset)] = feed

            for future in as_completed(futures_to_feed):
                feed = futures_to_feed[future]
                posts = future.result()
                feed_posts.append((feed, posts))

        for feed, posts in feed_posts:
            new_post_count = len(posts)
            for p in posts:
                p.save()
                PostAction.create(post_id=p.id, clicks=0, impressions=0, ctr=0)
                SimilarityProcessQueue.create(post_id=p.id)

            update_frequency = feed.status.update_frequency
            if new_post_count > 0:
                update_frequency = feed.status.update_frequency - 1
            elif new_post_count == 0:
                update_frequency = feed.status.update_frequency + 1

            if update_frequency < MIN_UPDATE_FREQ:
                update_frequency = MIN_UPDATE_FREQ
            elif update_frequency > MAX_UPDATE_FREQ:
                update_frequency = MAX_UPDATE_FREQ

            # Update the record in the status table
            feed.status.update(update_frequency=update_frequency, update_datetime=now())

    def run(self):
        """Run the processor."""
        if self.lock.is_locked():
            current_app.logger.info("Collection still in progress. Skipping.")
            return

        self.get_due_feeds()
        if len(self.due_feeds) == 0:
            current_app.logger.info("No dirty feeds to collect. Skipping.")
            return

        self.lock.create()
        current_app.logger.info(
            "Collecting new posts from {} dirty feeds.".format(len(self.due_feeds))
        )

        self.process_feeds()

        current_app.logger.info("Unlocking collector.")
        self.lock.remove()


def collect_posts(days=1):
    """Run the collector."""
    collector = Collector(days)
    collector.run()
