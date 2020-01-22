"""Similarity job."""
import re
from datetime import timedelta

import spacy
from flask import current_app

from aggrep import db
from aggrep.jobs.base import Job
from aggrep.models import Category, Feed, Post, Similarity, SimilarityProcessQueue
from aggrep.utils import now

new_line = re.compile(r"(/\n)")
ws = re.compile(r"\s+")
nlp = spacy.load("en_core_web_md")

BATCH_SIZE = 50
THRESHOLD = 0.825


def clean(text):
    """Normalize text."""
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = new_line.sub(" ", text)
    text = ws.sub(" ", text)
    return text.strip()


class Relater(Job):
    """Post relater job."""

    identifier = "RELATE"
    lock_timeout = 8

    def get_enqueued_posts(self, category):
        """Get enqueued posts."""
        similar_by_category = SimilarityProcessQueue.query.filter(
            SimilarityProcessQueue.post.has(Post.feed.has(Feed.category == category))
        ).all()

        return [eq.post.id for eq in similar_by_category]

    def set_post_cache(self, category):
        """Get recent posts in a given category."""
        delta = now() - timedelta(days=1)

        recent_posts = (
            Post.query.filter(Post.published_datetime >= delta)
            .filter(Post.feed.has(Feed.category == category))
            .all()
        )

        self.recent_posts = dict()
        for rp in recent_posts:
            doc = nlp(clean(rp.title))
            self.recent_posts[rp.id] = doc

    def process_batch(self, batch):
        """Process a batch of posts."""
        new_similarities = 0
        batch_ids = set([x for x in batch])

        for pid in batch:
            try:
                pdoc = self.recent_posts[pid]
            except KeyError:
                continue

            for rpid, rpdoc in self.recent_posts.items():
                if pid == rpid:
                    continue

                if rpid in batch_ids:
                    continue

                score = pdoc.similarity(rpdoc)
                if score >= THRESHOLD:
                    s_to_r = Similarity(source_id=pid, related_id=rpid)
                    db.session.add(s_to_r)
                    r_to_s = Similarity(related_id=pid, source_id=rpid)
                    db.session.add(r_to_s)
                    new_similarities += 2

        SimilarityProcessQueue.query.filter(
            SimilarityProcessQueue.post_id.in_(list(batch_ids))
        ).delete(synchronize_session="fetch")

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            self.lock.remove()
            raise

        return new_similarities

    def run(self):
        """Run the relater."""
        if self.lock.is_locked():
            if not self.lock.is_expired():
                current_app.logger.info(
                    "Similarity processing still in progress. Skipping."
                )
                return
            else:
                self.lock.remove()

        similar_queue_count = SimilarityProcessQueue.query.count()
        if similar_queue_count == 0:
            current_app.logger.info(
                "No posts in similarity processing queue. Skipping..."
            )
            return

        self.lock.create()
        current_app.logger.info(
            "Processing {} posts in similarity processing queue.".format(
                similar_queue_count
            )
        )

        new_similarities = 0
        for category in Category.query.all():
            enqueued_posts = self.get_enqueued_posts(category)
            if len(enqueued_posts) == 0:
                continue

            self.set_post_cache(category)
            start = 0
            while start < len(enqueued_posts):
                if not self.lock.is_locked() or self.lock.is_expired():
                    break
                end = start + BATCH_SIZE
                batch = enqueued_posts[start:end]
                new_similarities += self.process_batch(batch)
                start = end

        current_app.logger.info("Unlocking relater.")
        self.lock.remove()

        if new_similarities > 0:
            current_app.logger.info("Added {} similarities.".format(new_similarities))


def process_similarities():
    """Process enqueued similarities."""
    relater = Relater()
    relater.run()
