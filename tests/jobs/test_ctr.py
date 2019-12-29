"""Post processing unit tests."""
from datetime import timedelta
from decimal import Decimal
from random import randint

import pytest

from aggrep.jobs.ctr import CTR
from aggrep.models import JobLock, JobType, Post
from aggrep.utils import now
from tests.factories import PostFactory


@pytest.mark.usefixtures("db")
class TestCTR:
    """Click-through module tests."""

    def test_get_due_posts(self):
        """Test finding new posts."""

        ctr = CTR()
        due_posts = 0
        for instance in PostFactory.create_batch(20):
            instance.save()
            _click = randint(0, 5)
            _impression = randint(0, 10)
            instance.actions.update(clicks=_click, impressions=_impression)

            if _click > 0 and _impression > 0:
                due_posts += 1

        assert len(ctr.get_due_posts()) == due_posts

    def test_get_expired_posts(self):
        """Test finding expired posts."""

        days_ago = now() - timedelta(days=2)

        ctr = CTR()
        due_posts = 0
        for instance in PostFactory.create_batch(20):
            instance.update(published_datetime=days_ago)
            _click = randint(0, 5)
            _impression = randint(0, 10)

            instance.actions.update(clicks=_click, impressions=_impression)

            if _click > 0 and _impression > 0:
                due_posts += 1

        assert len(ctr.get_expired_posts()) == due_posts

    def test_update_ctr(self):
        """Test CTR update function."""

        ctr = CTR()
        clicks = []
        impressions = []
        for instance in PostFactory.create_batch(20):
            instance.save()
            _click = randint(0, 5)
            _impression = randint(0, 10)
            instance.actions.update(clicks=_click, impressions=_impression, ctr=0)

            clicks.append(_click)
            impressions.append(_impression)

        for post in Post.query.all():
            assert post.actions.ctr == 0

        ctr.run()

        for i, post in enumerate(Post.query.all()):
            try:
                ctr = Decimal(round(float(clicks[i] / impressions[i]), 3))
            except ZeroDivisionError:
                ctr = Decimal(0)
            assert post.actions.ctr == pytest.approx(ctr)

    def test_update_ctr_no_posts(self):
        """Test CTR update function."""

        days_ago = now() - timedelta(days=2)

        ctr = CTR()
        for instance in PostFactory.create_batch(20):
            instance.update(published_datetime=days_ago)
            _click = randint(0, 5)
            _impression = randint(0, 10)
            instance.actions.update(clicks=_click, impressions=_impression, ctr=0)

        ctr.run()

        for post in Post.query.all():
            assert post.actions.ctr == 0

    def test_process_entities_prior_lock(self):
        """Test processing with existing lock."""

        ctr = CTR()
        job_type = JobType.query.filter(JobType.job == "ANALYZE").first()

        clicks = []
        impressions = []
        for instance in PostFactory.create_batch(20):
            instance.save()
            _click = randint(0, 5)
            _impression = randint(0, 10)
            instance.actions.update(clicks=_click, impressions=_impression, ctr=0)

            clicks.append(_click)
            impressions.append(_impression)

        for post in Post.query.all():
            assert post.actions.ctr == 0

        JobLock.create(job=job_type)

        ctr.run()

        for post in Post.query.all():
            assert post.actions.ctr == 0

        assert JobLock.query.filter(JobLock.job == job_type).first() is not None

    def test_process_entities_expired_lock(self):
        """Test processing with expired lock."""

        ctr = CTR()
        job_type = JobType.query.filter(JobType.job == "ANALYZE").first()

        clicks = []
        impressions = []
        for instance in PostFactory.create_batch(20):
            instance.save()
            _click = randint(0, 5)
            _impression = randint(0, 10)
            instance.actions.update(clicks=_click, impressions=_impression, ctr=0)

            clicks.append(_click)
            impressions.append(_impression)

        for post in Post.query.all():
            assert post.actions.ctr == 0

        JobLock.create(job=job_type, lock_datetime=now() - timedelta(minutes=10))

        ctr.run()

        for i, post in enumerate(Post.query.all()):
            try:
                ctr = Decimal(round(float(clicks[i] / impressions[i]), 3))
            except ZeroDivisionError:
                ctr = Decimal(0)
            assert post.actions.ctr == pytest.approx(ctr)

        assert JobLock.query.filter(JobLock.job == job_type).first() is None
