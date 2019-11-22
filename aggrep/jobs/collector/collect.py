"""Post collection job."""
from datetime import timedelta, timezone

import feedparser
from flask import current_app

from aggrep import db
from aggrep.jobs.collector.post_parser import PostParser
from aggrep.models import EntityProcessQueue, Feed, JobLock, JobType, Post, PostAction, Source, Status
from aggrep.utils import now

MIN_UPDATE_FREQ = 1  # 2**1 minutes
MAX_UPDATE_FREQ = 8  # 2**8 minutes


def is_locked():
    """Check if the job is locked."""
    job_type = JobType.query.filter(JobType.job == 'COLLECT').first()
    prior_lock = JobLock.query.filter(JobLock.job == job_type).first()
    if prior_lock is not None:
        lock_datetime = prior_lock.lock_datetime.replace(tzinfo=timezone.utc)
        if lock_datetime >= now() - timedelta(minutes=8):
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


def get_source_posts(feed, archival_offset):
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

    job_type = JobType.query.filter(JobType.job == 'COLLECT').first()
    lock = JobLock.create(job=job_type, lock_datetime=now())
    current_app.logger.info(
        "Collecting new posts from {} dirty feeds.".format(len(due_feeds))
    )

    post_cache = dict()
    collection_offset = now() - timedelta(days=days)
    archival_offset = now() - timedelta(days=days * 2)

    for feed in due_feeds:
        link_urls = post_cache.get(feed.source.id, None)
        if link_urls is None:
            link_urls = get_source_cache(feed, archival_offset)
            post_cache[feed.source.id] = link_urls

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
