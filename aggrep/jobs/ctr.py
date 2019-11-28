"""Post Action analytics update job."""
from flask import current_app

from aggrep.jobs.base import Job
from aggrep.models import PostAction


class CTR(Job):
    """CTR job."""

    identifier = "ANALYZE"
    lock_timeout = 4

    def get_due_posts(self):
        """Get posts with clicks and impressions for update."""

        return [
            p
            for p in PostAction.query.filter(
                PostAction.impressions > 0, PostAction.clicks > 0
            ).all()
        ]

    def run(self):
        """Update post stats."""

        if self.lock.is_locked():
            if not self.lock.is_expired():
                current_app.logger.info("CTR processing still in progress. Skipping.")
                return
            else:
                self.lock.remove()

        due_posts = self.get_due_posts()
        if len(due_posts) == 0:
            current_app.logger.info("No post actions to update. Skipping.")
            return

        self.lock.create()
        current_app.logger.info(
            "Updating posts stats for {} posts.".format(len(due_posts))
        )

        for p in due_posts:
            p.ctr = p.clicks / p.impressions
            p.save()

        current_app.logger.info("Unlocking analyzer.")
        self.lock.remove()


def update_ctr():
    """Update ctrs."""
    ctr = CTR()
    ctr.run()
