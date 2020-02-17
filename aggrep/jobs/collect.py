"""Post collection job."""
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser
import requests
from bs4 import BeautifulSoup
from flask import current_app

from aggrep.jobs.base import Job
from aggrep.models import (
    Category,
    EntityProcessQueue,
    Feed,
    Post,
    PostAction,
    Source,
    Status,
)
from aggrep.utils import now

MIN_UPDATE_FREQ = 3  # 2**3 minutes (8)
MAX_UPDATE_FREQ = 6  # 2**8 minutes (64)
BATCH_SIZE = 10


source_cache = defaultdict(set)


class OpenGraphParser:
    """Parse an article's OpenGraph data for richer content."""

    def __init__(self, url):
        """Parser init."""
        self.attrs = dict()
        self._url = url
        self.parse()

    def _get(self, attr):
        """Get an OG attribute."""
        return self.attrs.get(attr)

    @property
    def url(self):
        """Get the OG URL attribute."""
        return self._get("url")

    @property
    def title(self):
        """Get the OG title attribute."""
        return self._get("title")

    @property
    def image(self):
        """Get the OG image attribute."""
        return self._get("image")

    @property
    def description(self):
        """Get the OG description attribute."""
        return self._get("description")

    def fetch(self):
        """Fetch OG data."""
        headers = {"User-Agent": "Aggregate Report/1.0"}

        content = requests.get(self._url, headers=headers, timeout=1)
        content.raise_for_status()
        return content.text

    def parse(self):
        """Fetch and parse OG data."""
        content = self.fetch()
        soup = BeautifulSoup(content, "html5lib")

        og_tags = soup.findAll(property=re.compile(r"^og"))
        for tag in og_tags:
            if tag.has_attr("content"):
                self.attrs[tag["property"][3:]] = tag["content"]


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

        if len(desc) > 255:
            desc = desc[:255]

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
    lock_timeout = 6

    def __init__(self, ndays=1):
        """Init."""
        super().__init__()
        self._collection_offset = now() - timedelta(days=ndays)
        self._archival_offset = now() - timedelta(days=ndays + 1)

    def get_due_feeds(self, category):
        """Get feeds in need of processing."""
        due_feeds = []
        processable_feeds = (
            Status.query.filter(
                Status.feed.has(Feed.category == category), Status.active == True
            )
            .order_by(Status.id)
            .all()
        )
        for status in processable_feeds:
            update_datetime = status.update_datetime.replace(tzinfo=timezone.utc)

            status_offset = 2 ** status.update_frequency
            if update_datetime <= now() - timedelta(minutes=status_offset):
                due_feeds.append(status.feed)

        return due_feeds

    def get_source_posts(self, source):
        """Get posts from a source."""
        source_posts = Post.query.filter(
            Post.published_datetime >= self._archival_offset
        ).filter(Post.feed.has(Feed.source.has(Source.id == source.id)))

        source_cache[source.title].update(post.link for post in source_posts)

    def process_feeds(self, due_feeds):
        """Process feeds ready for review."""
        feed_posts = []
        with ThreadPoolExecutor() as executor:
            futures_to_feed = {}

            for feed in due_feeds:
                self.get_source_posts(feed.source)
                link_urls = source_cache[feed.source.title]
                futures_to_feed[
                    executor.submit(
                        process_posts, feed, link_urls, self._collection_offset
                    )
                ] = feed

            for future in as_completed(futures_to_feed):
                current_app.logger.info("Processing feed {}.".format(feed.id))
                feed = futures_to_feed[future]
                posts = future.result()
                feed_posts.append((feed, posts))

        for feed, posts in feed_posts:
            current_app.logger.info("Saving posts from feed {}.".format(feed.id))
            new_post_count = len(posts)
            for p in posts:
                p.save()
                PostAction.create(post_id=p.id, clicks=0, impressions=0, ctr=0)
                EntityProcessQueue.create(post_id=p.id)

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
            if not self.lock.is_expired():
                current_app.logger.info("Collection still in progress. Skipping.")
                return
            else:
                self.lock.remove()

        self.lock.create()

        for category in Category.query.all():
            due_feeds = self.get_due_feeds(category)
            if len(due_feeds) == 0:
                current_app.logger.info(
                    "No dirty feeds to collect in category {}. Skipping.".format(
                        category.title
                    )
                )
                continue

            current_app.logger.info(
                "{} dirty feeds in category {}.".format(len(due_feeds), category.title)
            )

            start = 0
            while start < len(due_feeds):
                if not self.lock.is_locked() or self.lock.is_expired():
                    break
                end = start + BATCH_SIZE
                batch = due_feeds[start:end]
                self.process_feeds(batch)
                start = end

        current_app.logger.info("Unlocking collector.")
        self.lock.remove()


def collect_posts(days=1):
    """Run the collector."""
    collector = Collector(days)
    collector.run()
