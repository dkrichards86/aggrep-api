"""Celery worker runner."""

from celery import Celery

from aggrep import create_app
from aggrep.tasks import (
    task_collect_posts,
    task_process_entities,
    task_process_similarities,
    task_update_ctr,
)

MINUTE = 60


def create_celery(app):
    """Create an app for Celery jobs."""

    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL'],
    )

    celery.conf.update(app.config)
    TaskBase = celery.Task  # noqa

    class ContextTask(TaskBase):
        """Forward app context to Celery tasks."""

        abstract = True

        def __call__(self, *args, **kwargs):
            """Wrap tasks in app context."""
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


flask_app = create_app()
celery = create_celery(flask_app)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Configure periodic jobs."""

    sender.add_periodic_task(MINUTE * 4, task_collect_posts, name="collect posts")
    sender.add_periodic_task(MINUTE * 4, task_process_entities, name="process entities")
    sender.add_periodic_task(MINUTE * 4, task_process_similarities, name="process similarities")
    sender.add_periodic_task(MINUTE * 15, task_update_ctr, name="update stats")
