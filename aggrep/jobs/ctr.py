"""Post Action analytics update job."""
from datetime import timedelta

from flask import current_app

from aggrep.jobs.base import Job
from aggrep.models import Post, PostAction
from aggrep.utils import now


class CTR(Job):
    """CTR job."""

    identifier = "ANALYZE"
    lock_timeout = 4

    def get_due_posts(self):
        """Get posts with clicks and impressions for update."""
        delta = now() - timedelta(days=1)

        return PostAction.query.filter(
            PostAction.post.has(Post.published_datetime >= delta),
            PostAction.impressions > 0,
            PostAction.clicks > 0,
        ).all()

    def get_expired_posts(self):
        """Get posts with clicks and impressions for update."""
        delta = now() - timedelta(days=1)

        return PostAction.query.filter(
            PostAction.post.has(Post.published_datetime < delta),
            PostAction.impressions > 0,
            PostAction.clicks > 0,
        ).all()

    def run(self):
        """Update post stats."""

        if self.lock.is_locked():
            if not self.lock.is_expired():
                current_app.logger.info("CTR processing still in progress. Skipping.")
                return
            else:
                self.lock.remove()

        self.lock.create()

        due_posts = self.get_due_posts()
        if len(due_posts) > 0:
            current_app.logger.info(
                "Updating posts stats for {} posts.".format(len(due_posts))
            )
            for p in due_posts:
                p.ctr = p.clicks / p.impressions
                p.save()
        else:
            current_app.logger.info("No post actions to update. Skipping.")

        expired_posts = self.get_expired_posts()
        if len(expired_posts) > 0:
            current_app.logger.info(
                "Expired posts stats for {} posts.".format(len(expired_posts))
            )
            for p in expired_posts:
                p.ctr = 0
                p.save()
        else:
            current_app.logger.info("No post actions to update. Skipping.")

        current_app.logger.info("Unlocking analyzer.")
        self.lock.remove()


def update_ctr():
    """Update ctrs."""
    ctr = CTR()
    ctr.run()
