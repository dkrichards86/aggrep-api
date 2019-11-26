"""Post relater unit tests."""
from collections import defaultdict
from datetime import timedelta

import pytest

from aggrep.jobs.relate import get_entity_cache, is_locked
from aggrep.models import JobLock, JobType
from aggrep.utils import now


@pytest.mark.usefixtures("db")
class TestRelate:
    """Relater module tests."""

    def test_is_locked(self):
        """Test locking."""

        job_type = JobType.query.filter(JobType.job == "RELATE").first()
        assert is_locked() is False

        lock = JobLock.create(job=job_type, lock_datetime=now())
        assert is_locked() is True

        lock.delete()
        assert is_locked() is False

        lock = JobLock.create(job=job_type, lock_datetime=now() - timedelta(minutes=10))
        assert is_locked() is False

    def test_get_entity_cache(self):
        """Test fetching the entity cache."""
        assert type(get_entity_cache()) == defaultdict
