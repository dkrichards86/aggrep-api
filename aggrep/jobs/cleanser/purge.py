"""Post collection job."""
from datetime import timedelta, timezone

from flask import current_app

from aggrep import db
from aggrep.models import Post
from aggrep.utils import now

BATCH_SIZE = 500

def purge_posts():
    current_app.logger.info("Preparing to remove expired posts and relationships.")
    delta = now() - timedelta(days=7)
    expired_posts = Post.query.filter(Post.published_datetime < delta).all()

    expired_count = 0
    start = 0
    current_app.logger.info(len(expired_posts))
    while start < len(expired_posts):
        current_app.logger.info("Batch")
        end = start + BATCH_SIZE
        batch = expired_posts[start:end]

        post_ids = set()
        for post in batch:
            expired_count += 1
            post_ids.add(post.id)

        Post.query.filter(Post.id.in_(list(post_ids))).delete(synchronize_session="fetch")

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        start = end

    current_app.logger.info("Removed {} expired posts and relationships.".format(expired_count))

if __name__ == "__main__":
    purge_posts()
