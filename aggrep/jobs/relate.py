"""Similarity job."""
from collections import defaultdict
from datetime import timedelta

from flask import current_app

from aggrep import db
from aggrep.jobs.base import Job
from aggrep.models import Post, Similarity, SimilarityProcessQueue
from aggrep.utils import now, overlap

BATCH_SIZE = 100
THRESHOLD = 0.75


class Relater(Job):
    """Post relater job."""

    identifier = "RELATE"
    lock_timeout = 8

    def get_enqueued_posts(self):
        """Get enqueued posts."""
        return [eq.post for eq in SimilarityProcessQueue.query.all()]

    def get_entity_cache(self):
        """Get entities from recent posts."""
        delta = now() - timedelta(days=2)
        entity_cache = defaultdict(set)
        recent_posts = Post.query.filter(Post.published_datetime >= delta).all()
        for rp in recent_posts:
            for e in rp.entities:
                entity_cache[e.entity].add(rp.id)

        self.entity_cache = entity_cache

    def process_batch(self, batch):
        """Process a batch of posts."""
        post_ids = []
        new_similarities = 0

        for post in batch:
            post_ids.append(post.id)
            entities = [e.entity for e in post.entities]
            entity_set = set(entities)

            intersecting_post_ids = set()
            for e in entities:
                cached = self.entity_cache.get(e)
                if cached is None:
                    continue
                intersecting_post_ids |= self.entity_cache[e]

            keyworded_posts = Post.query.filter(
                Post.id.in_(list(intersecting_post_ids))
            ).all()

            seen_post_ids = set()

            for rp in keyworded_posts:
                if rp.id == post.id:
                    continue

                if rp.id in seen_post_ids:
                    continue

                related_entity_set = set([e.entity for e in rp.entities])

                score = overlap(entity_set, related_entity_set)
                if score >= THRESHOLD:
                    s_to_r = Similarity(source_id=post.id, related_id=rp.id)
                    db.session.add(s_to_r)
                    r_to_s = Similarity(related_id=post.id, source_id=rp.id)
                    db.session.add(r_to_s)
                    new_similarities += 2

                seen_post_ids.add(rp.id)

        SimilarityProcessQueue.query.filter(
            SimilarityProcessQueue.post_id.in_(post_ids)
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

        enqueued_posts = self.get_enqueued_posts()
        if len(enqueued_posts) == 0:
            current_app.logger.info(
                "No posts in similarity processing queue. Skipping..."
            )
            return

        self.lock.create()
        current_app.logger.info(
            "Processing {} posts in similarity queue.".format(len(enqueued_posts))
        )

        self.get_entity_cache()
        new_similarities = 0
        start = 0
        while start < len(enqueued_posts):
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
