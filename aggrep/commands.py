"""Click commands."""
import csv
import os
from datetime import datetime, timedelta, timezone
from glob import glob
from subprocess import call

import click
from environs import Env
from flask import current_app
from flask.cli import with_appcontext

from aggrep.models import Category, Feed, JobLock, JobType, Source, Status
from aggrep.utils import slugify

env = Env()
env.read_env()

APP_ROOT = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.join(APP_ROOT, os.pardir)
TEST_PATH = os.path.join(APP_ROOT, "tests")
JOB_TYPES = ("COLLECT", "RELATE", "ANALYZE", "PROCESS")


@click.command()
@click.option("--show-missing", default=False, is_flag=True, help="Show missing lines")
@click.option("--verbose", default=False, is_flag=True, help="Use verbose output")
@click.option("--fail-fast", default=False, is_flag=True, help="Fail fast")
def test(show_missing, verbose, fail_fast):
    """Run the tests."""

    command_line = ["pytest"]

    if verbose:
        command_line.append("-v")

    if fail_fast:
        command_line.append("-x")

    command_line.extend(["--cov=aggrep"])

    if not show_missing:
        command_line.extend(["--cov-report", "term:skip-covered"])
    else:
        command_line.extend(["--cov-report", "term-missing:skip-covered"])

    command_line.append("tests/")

    click.echo("Running tests: {}".format(" ".join(command_line)))
    rv = call(command_line)
    exit(rv)


@click.command()
@click.option(
    "-f",
    "--fix-imports",
    default=True,
    is_flag=True,
    help="Fix imports using isort, before linting",
)
@click.option(
    "-c",
    "--check",
    default=False,
    is_flag=True,
    help="Don't make any changes to files, just confirm they are formatted correctly",
)
def lint(fix_imports, check):
    """Lint and check code style with black, flake8 and isort."""
    skip = ["requirements", "migrations"]
    root_files = glob("*.py")
    root_directories = [
        name for name in next(os.walk("."))[1] if not name.startswith(".")
    ]
    files_and_directories = [
        arg for arg in root_files + root_directories if arg not in skip
    ]

    def execute_tool(description, *args):
        """Execute a checking tool with its arguments."""
        command_line = list(args) + files_and_directories
        click.echo("{}: {}".format(description, " ".join(command_line)))
        rv = call(command_line)
        if rv != 0:
            exit(rv)

    isort_args = ["-rc"]
    black_args = []
    if check:
        isort_args.append("-c")
        black_args.append("--check")
    if fix_imports:
        execute_tool("Fixing import order", "isort", *isort_args)
    execute_tool("Formatting style", "black", *black_args)
    execute_tool("Checking code style", "flake8")


@click.command()
@with_appcontext
def seed_feeds():
    """Add new feeds to the database."""
    filepath = os.path.join(PROJECT_ROOT, "feeds.csv")

    status_time = datetime.now(timezone.utc)
    status_offset = status_time - timedelta(days=1)

    feed_cache = set([f.url for f in Feed.query.all()])

    with open(filepath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["url"] not in feed_cache:
                category = Category.query.filter_by(title=row["category"]).first()
                if not category:
                    current_app.logger.info("No category '{}'".format(row["category"]))
                source = Source.query.filter_by(title=row["source"]).first()
                if not source:
                    current_app.logger.info("Adding source '{}'".format(row["source"]))
                    source = Source.create(
                        title=row["source"], slug=slugify(row["source"])
                    )

                feed = Feed.create(
                    category_id=category.id, source_id=source.id, url=row["url"]
                )
                Status.create(
                    feed_id=feed.id, update_datetime=status_offset, update_frequency=3
                )
                feed_cache.add(row["url"])


@click.command()
@with_appcontext
def seed_categories():
    """Seed the database with categories."""
    categories = (
        "News",
        "Business",
        "Technology",
        "Sports",
        "Entertainment",
        "Science",
        "Health",
    )
    for cat in categories:
        c = Category.query.filter_by(title=cat).first()
        if not c:
            Category.create(title=cat, slug=slugify(cat))


@click.command()
@with_appcontext
def seed_locks():
    """Seed the database with job locks."""
    for l in JOB_TYPES:
        JobType.create(job=l)


@click.command()
@click.option("--identifier", type=click.Choice(JOB_TYPES))
@with_appcontext
def unlock_job(identifier):
    """Unlock a job."""
    job_type = JobType.query.filter(JobType.job == identifier).first()
    job_lock = JobLock.query.filter(JobLock.job == job_type).first()
    job_lock.delete()


@click.command()
@click.option("--feed-id", type=click.Choice(JOB_TYPES))
@with_appcontext
def activate_feed(feed_id):
    """Activate a feed."""
    status = Status.query.get(feed_id)
    status.update(active=True)


@click.command()
@click.option("--feed-id", type=click.Choice(JOB_TYPES))
@with_appcontext
def deactivate_feed(feed_id):
    """Deactivate a feed."""
    status = Status.query.get(feed_id)
    status.update(active=False)


@click.command()
@click.option("-d", "--days", default=3, help="Number of days to collect")
@with_appcontext
def collect(days=1):
    """Collect recent posts."""
    from aggrep.jobs.collect import collect_posts

    collect_posts(days=days)


@click.command()
@with_appcontext
def process():
    """Process recent posts."""
    from aggrep.jobs.entities import process_entities

    process_entities()


@click.command()
@with_appcontext
def relate():
    """Relate recent posts."""
    from aggrep.jobs.relate import process_similarities

    process_similarities()


@click.command()
@with_appcontext
def updatestats():
    """Update post stats."""
    from aggrep.jobs.ctr import update_ctr

    update_ctr()
