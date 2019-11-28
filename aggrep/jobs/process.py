"""Entity processing job."""
import re
import string
from collections import Counter

import spacy
from flask import current_app

from aggrep import db
from aggrep.jobs.base import Job
from aggrep.models import Entity, EntityProcessQueue, SimilarityProcessQueue

punct_table = str.maketrans(dict.fromkeys(string.punctuation))
new_line = re.compile(r"(/\n)")
ws = re.compile(r"\s+")
nlp = spacy.load("en_core_web_sm")


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
BATCH_SIZE = 500
TOP_N_ENTITIES = 8


def clean(text):
    """Normalize text."""
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = new_line.sub(" ", text)
    text = ws.sub(" ", text)
    return text.strip()


def extract(text):
    """Extract entities from a document."""
    entities = []
    doc = nlp(text)

    for span in doc.ents:
        for token in span:
            if len(token) < 2 or len(token) > 40:
                continue

            if token.is_punct or token.is_stop or token.is_digit:
                continue

            if token.ent_type_ in EXCLUDES:
                continue

            entity = token.lemma_.lower()
            entities.append(entity.translate(punct_table))

    return entities


class Processor(Job):
    """Post processor job."""

    identifier = "PROCESS"
    lock_timeout = 8

    def get_enqueued_posts(self):
        """Get enqueued posts."""
        return [eq.post for eq in EntityProcessQueue.query.all()]

    def process_batch(self, batch):
        """Process a batch of posts."""
        post_ids = []
        new_entities = 0
        for post in batch:
            post_ids.append(post.id)
            post_has_entities = False

            if not post.desc:
                continue

            post_doc = extract(clean("{}. {}".format(post.title, post.desc)))
            entity_counter = Counter()
            for word in post_doc:
                entity_counter[word] += 1

            # Most feed descriptions are summaries of the article. In some feeds though, the
            # description is the article itself. In these cases, we will end up with a significant
            # amount of unusuable entities. Since we use set comparisons for relating posts. we will
            # never relate to the descriptive post. Limit the entities to the top 10 so we have a
            # fighting chance of associating the post.
            for word, _ in entity_counter.most_common(TOP_N_ENTITIES):
                post_has_entities = True
                e = Entity(entity=word, post_id=post.id)
                db.session.add(e)
                new_entities += 1

            if post_has_entities:
                s = SimilarityProcessQueue(post_id=post.id)
                db.session.add(s)

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
    processor = Processor()
    processor.run()
