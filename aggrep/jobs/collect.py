"""Post collection job."""
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser
from bs4 import BeautifulSoup
from flask import current_app

from aggrep import db
from aggrep.models import (
    EntityProcessQueue,
    Feed,
    JobLock,
    JobType,
    Post,
    PostAction,
    Source,
    Status,
)
from aggrep.utils import now

MIN_UPDATE_FREQ = 1  # 2**1 minutes
MAX_UPDATE_FREQ = 8  # 2**8 minutes
LOCK_TIMEOUT = 8

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


def is_locked():
    """Check if the job is locked."""
    job_type = JobType.query.filter(JobType.job == "COLLECT").first()
    prior_lock = JobLock.query.filter(JobLock.job == job_type).first()
    if prior_lock is not None:
        lock_datetime = prior_lock.lock_datetime.replace(tzinfo=timezone.utc)
        if lock_datetime >= now() - timedelta(minutes=LOCK_TIMEOUT):
            return True
        else:
            prior_lock.delete()

    return False


def get_due_feeds():
    """Get feeds in need of processing."""
    due_feeds = []
    for status in Status.query.order_by(Status.id).all():
        update_datetime = status.update_datetime.replace(tzinfo=timezone.utc)

        status_offset = 2 ** status.update_frequency
        if update_datetime <= now() - timedelta(minutes=status_offset):
            due_feeds.append(status.feed)

    return due_feeds


def get_source_cache(feed, archival_offset):
    """Get posts from a source."""
    source_posts = Post.query.filter(Post.published_datetime >= archival_offset).filter(
        Post.feed.has(Feed.source.has(Source.id == feed.source.id))
    )

    return set(post.link for post in source_posts)


def collect_posts(days=1):
    """Collect posts from the pasy <days> days."""
    if is_locked():
        current_app.logger.info("Collection still in progress. Skipping.")
        return

    due_feeds = get_due_feeds()
    if len(due_feeds) == 0:
        current_app.logger.info("No dirty feeds to collect. Skipping.")
        return

    job_type = JobType.query.filter(JobType.job == "COLLECT").first()
    lock = JobLock.create(job=job_type, lock_datetime=now())
    current_app.logger.info(
        "Collecting new posts from {} dirty feeds.".format(len(due_feeds))
    )

    collection_offset = now() - timedelta(days=days)
    archival_offset = now() - timedelta(days=days + 1)

    for feed in due_feeds:
        link_urls = get_source_cache(feed, archival_offset)

        # Get the actual feed data
        feed_data = feedparser.parse(feed.url)

        # Prep the bulk storage containers
        new_post_count = 0
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

            if post.link not in link_urls:
                # If this particular post has not been processed
                # previously, process it.
                link_urls.add(post.link)

                # Build and save the post object.
                p = Post.create(
                    feed_id=feed.id,
                    title=post.title,
                    desc=post.description,
                    link=post.link,
                    published_datetime=post_datetime,
                )
                pa = PostAction.create(post_id=p.id, clicks=0, impressions=0, ctr=0)
                e = EntityProcessQueue(post_id=p.id)
                db.session.add(p)
                db.session.add(pa)
                db.session.add(e)

                new_post_count += 1

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            lock.delete()
            raise

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
        if new_post_count > 0:
            current_app.logger.info(
                "Added {} new posts for feed {}.".format(new_post_count, feed)
            )

    current_app.logger.info("Unlocking collector.")
    lock.delete()


if __name__ == "__main__":
    collect_posts()
