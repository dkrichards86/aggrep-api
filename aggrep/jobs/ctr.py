"""Post Action analytics update job."""
from datetime import timedelta, timezone

from flask import current_app

from aggrep.models import JobLock, JobType, PostAction
from aggrep.utils import now


LOCK_TIMEOUT = 8


def is_locked():
    """Check if the job is locked."""
    job_type = JobType.query.filter(JobType.job == "ANALYZE").first()
    prior_lock = JobLock.query.filter(JobLock.job == job_type).first()
    if prior_lock is not None:
        lock_datetime = prior_lock.lock_datetime.replace(tzinfo=timezone.utc)
        if lock_datetime >= now() - timedelta(minutes=LOCK_TIMEOUT):
            return True
        else:
            prior_lock.delete()

    return False


def get_due_posts():
    """Get posts with clicks and impressions for update."""

    return [
        p
        for p in PostAction.query.filter(
            PostAction.impressions > 0, PostAction.clicks > 0
        ).all()
    ]


def update_ctr():
    """Update post stats."""

    if is_locked():
        current_app.logger.info("Collection still in progress. Skipping.")
        return

    due_posts = get_due_posts()
    if len(due_posts) == 0:
        current_app.logger.info("No post actions to update. Skipping.")
        return

    job_type = JobType.query.filter(JobType.job == "ANALYZE").first()
    lock = JobLock.create(job=job_type, lock_datetime=now())
    current_app.logger.info("Updating posts stats for {} posts.".format(len(due_posts)))

    for p in due_posts:
        p.ctr = p.clicks / p.impressions
        p.save()

    current_app.logger.info("Unlocking analyzer.")
    lock.delete()


if __name__ == "__main__":
    update_ctr()
