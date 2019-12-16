"""Similarity job."""
from collections import defaultdict
from datetime import timedelta

from flask import current_app

from aggrep import db
from aggrep.jobs.base import Job
from aggrep.models import Category, Feed, Post, Similarity, SimilarityProcessQueue
from aggrep.utils import now, overlap

BATCH_SIZE = 100
THRESHOLD = 0.75


class Relater(Job):
    """Post relater job."""

    identifier = "RELATE"
    lock_timeout = 8

    def get_enqueued_posts(self, category):
        """Get enqueued posts."""
        similar_by_category = SimilarityProcessQueue.query.filter(
            SimilarityProcessQueue.post.has(Post.feed.has(Feed.category == category))
        ).all()

        return [eq.post for eq in similar_by_category]

    def set_entity_cache(self, category):
        """Get entities from recent posts."""
        delta = now() - timedelta(days=2)
        entity_cache = defaultdict(set)

        recent_posts = (
            Post.query.filter(Post.published_datetime >= delta)
            .filter(Post.feed.has(Feed.category == category))
            .all()
        )

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

            unioned_post_ids = set()
            for e in entities:
                cached = self.entity_cache.get(e)
                if cached is None:
                    continue
                unioned_post_ids |= self.entity_cache[e]

            keyworded_posts = Post.query.filter(
                Post.id.in_(list(unioned_post_ids))
            ).all()

            for rp in keyworded_posts:
                if rp.id == post.id:
                    continue

                related_entity_set = set([e.entity for e in rp.entities])

                score = overlap(entity_set, related_entity_set)
                if score >= THRESHOLD:
                    s_to_r = Similarity(source_id=post.id, related_id=rp.id)
                    db.session.add(s_to_r)
                    r_to_s = Similarity(related_id=post.id, source_id=rp.id)
                    db.session.add(r_to_s)
                    new_similarities += 2

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

        self.lock.create()
        similar_queue_count = SimilarityProcessQueue.query.count()
        if similar_queue_count == 0:
            current_app.logger.info(
                "No posts in similarity processing queue. Skipping..."
            )
            return

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

            self.set_entity_cache(category)
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
