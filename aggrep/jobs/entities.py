"""Entity processing job."""
import html
import re

import spacy
from flask import current_app
from sqlalchemy import desc

from aggrep import db
from aggrep.jobs.base import Job
from aggrep.models import Entity, EntityProcessQueue

new_line = re.compile(r"(/\n)")
ws = re.compile(r"\s+")
nlp = spacy.load("en_core_web_md")


BATCH_SIZE = 250
PER_RUN_LIMIT = 3000
EXCLUDES = [
    "LANGUAGE",
    "DATE",
    "TIME",
    "PERCENT",
    "MONEY",
    "QUANTITY",
    "ORDINAL",
    "CARDINAL",
]


def clean(text):
    """Normalize text."""
    text = html.unescape(text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = new_line.sub(" ", text)
    text = ws.sub(" ", text)
    return text.strip()


def extract(text):
    """Extract entities from a document."""
    entities = set()
    doc = nlp(text)

    for span in doc.ents:
        if span.label_ in EXCLUDES:
            continue

        if len(span.text) < 2 or len(span.text) > 40:
            continue

        entities.add(span.text)

    return entities


class EntityExtractor(Job):
    """EntityExtractor job."""

    identifier = "PROCESS"
    lock_timeout = 8

    def get_enqueued_posts(self):
        """Get enqueued posts."""
        posts = EntityProcessQueue.query.order_by(
            desc(EntityProcessQueue.id)
        ).limit(PER_RUN_LIMIT).all()

        return [eq.post for eq in posts]

    def process_batch(self, batch):
        """Process a batch of posts."""
        post_ids = []
        new_entities = 0
        for post in batch:
            if post is None:
                continue

            post_ids.append(post.id)

            if not post.desc:
                continue

            post_doc = extract(clean("{}. {}".format(post.title, post.desc)))
            for word in post_doc:
                e = Entity(entity=word, post_id=post.id)
                db.session.add(e)
                new_entities += 1

        EntityProcessQueue.query.filter(
            EntityProcessQueue.post_id.in_(post_ids)
        ).delete(synchronize_session="fetch")

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            self.lock.remove()
            raise

        return new_entities

    def run(self):
        """Process entities."""
        if self.lock.is_locked():
            if not self.lock.is_expired():
                current_app.logger.info("Processing still in progress. Skipping.")
                return
            else:
                self.lock.remove()

        enqueued_posts = self.get_enqueued_posts()
        if len(enqueued_posts) == 0:
            current_app.logger.info("No posts in entity processing queue. Skipping...")
            return

        self.lock.create()
        current_app.logger.info(
            "Processing {} posts in entity queue.".format(len(enqueued_posts))
        )

        new_entities = 0
        start = 0
        while start < len(enqueued_posts):
            if not self.lock.is_locked() or self.lock.is_expired():
                break

            end = start + BATCH_SIZE
            batch = enqueued_posts[start:end]
            new_entities += self.process_batch(batch)
            start = end

        current_app.logger.info("Unlocking processor.")
        self.lock.remove()

        if new_entities > 0:
            current_app.logger.info("Added {} entities.".format(new_entities))


def process_entities():
    """Process entities."""
    processor = EntityExtractor()
    processor.run()
