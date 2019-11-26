"""Celery task definitions."""

from celery.signals import task_postrun
from celery.utils.log import get_task_logger

from aggrep import celery, db
from aggrep.jobs.collect import collect_posts
from aggrep.jobs.ctr import update_ctr
from aggrep.jobs.process import process_entities
from aggrep.jobs.relate import process_similarities

logger = get_task_logger(__name__)


@celery.task
def task_collect_posts():
    """Post collection task."""
    collect_posts()


@celery.task
def task_process_entities():
    """Post processing task."""
    process_entities()


@celery.task
def task_process_similarities():
    """Post relation task."""
    process_similarities()


@celery.task
def task_update_ctr():
    """Update post stats."""

    update_ctr()


@task_postrun.connect
def close_session(*args, **kwargs):
    """Drop Flask-SWLAlchemy session after tasks."""
    # Flask SQLAlchemy will automatically create new sessions for you from
    # a scoped session factory, given that we are maintaining the same app
    # context, this ensures tasks have a fresh session (e.g. session errors
    # won't propagate across tasks)
    db.session.remove()
