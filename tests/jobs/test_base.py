"""Base job unit tests."""
from datetime import timedelta

import pytest

from aggrep.jobs.base import Lock
from aggrep.models import JobLock, JobType
from aggrep.utils import now


@pytest.mark.usefixtures("db")
class TestLock:
    """Collection module tests."""

    def test_is_locked(self):
        """Test locking."""

        lock = Lock("COLLECT", 8)

        job_type = JobType.query.filter(JobType.job == "COLLECT").first()
        assert lock.is_locked() is False

        JobLock.create(job=job_type, lock_datetime=now())
        assert lock.is_locked() is True

        job_lock = JobLock.query.filter(JobLock.job == job_type).first()
        job_lock.delete()
        assert lock.is_locked() is False

        JobLock.create(job=job_type, lock_datetime=now() - timedelta(minutes=10))
        assert lock.is_locked() is True

    def test_create(self):
        """Test lock creation."""

        lock = Lock("RELATE", 8)
        assert lock.is_locked() is False

        lock.create()
        assert lock.is_locked() is True

    def test_remove(self):
        """Test lock removal."""

        lock = Lock("ANALYZE", 8)
        lock.create()
        assert lock.is_locked() is True

        lock.remove()
        assert lock.is_locked() is False

    def test_is_expired(self):
        """Test lock expiration."""

        lock = Lock("PROCESS", 8)
        assert lock.is_expired() is False

        lock.create()
        assert lock.is_expired() is False

        lock.remove()
        assert lock.is_expired() is False

        job_type = JobType.query.filter(JobType.job == "PROCESS").first()
        JobLock.create(job=job_type, lock_datetime=now() - timedelta(minutes=10))
        assert lock.is_expired() is True
