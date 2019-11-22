"""Similarity job."""
from collections import defaultdict
from datetime import timedelta, timezone

from flask import current_app

from aggrep import db
from aggrep.models import JobLock, JobType, Post, Similarity, SimilarityProcessQueue
from aggrep.utils import now, overlap

BATCH_SIZE = 100
THRESHOLD = 0.75


def process_similarities():
    """Process posts for similarities."""
    job_type = JobType.query.filter(JobType.job == 'RELATE').first()
    prior_lock = JobLock.query.filter(JobLock.job == job_type).first()
    if prior_lock is not None:
        lock_datetime = prior_lock.lock_datetime.replace(tzinfo=timezone.utc)
        if lock_datetime >= now() - timedelta(minutes=8):
            current_app.logger.info(
                "Similarity processing still in progress. Skipping."
            )
            return
        else:
            prior_lock.delete()

    enqueued_posts = [eq.post for eq in SimilarityProcessQueue.query.all()]
    if len(enqueued_posts) == 0:
        current_app.logger.info("No posts in similarity processing queue. Skipping...")
        return

    job_type = JobType.query.filter(JobType.job == 'RELATE').first()
    lock = JobLock.create(job=job_type, lock_datetime=now())

    current_app.logger.info(
        "Processing {} posts in similarity queue.".format(len(enqueued_posts))
    )
    new_similarities = 0
    delta = now() - timedelta(days=2)

    entity_cache = defaultdict(set)
    recent_posts = Post.query.filter(Post.published_datetime >= delta).all()
    for rp in recent_posts:
        for e in rp.entities:
            entity_cache[e.entity].add(rp.id)

    start = 0
    while start < len(enqueued_posts):
        end = start + BATCH_SIZE
        batch = enqueued_posts[start:end]
        post_ids = []

        for post in batch:
            post_ids.append(post.id)
            entities = [e.entity for e in post.entities]
            entity_set = set(entities)

            intersecting_post_ids = set()
            for e in entities:
                cached = entity_cache.get(e)
                if cached is None:
                    continue
                intersecting_post_ids = intersecting_post_ids.union(entity_cache[e])

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
            lock.delete()
            raise

        start = end
        end += BATCH_SIZE

    current_app.logger.info("Unlocking relater.")
    lock.delete()

    if new_similarities > 0:
        current_app.logger.info("Added {} similarities.".format(new_similarities))
