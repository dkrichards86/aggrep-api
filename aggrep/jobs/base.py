"""Base job tools."""
from datetime import timedelta, timezone

from aggrep.models import JobLock, JobType
from aggrep.utils import now


class Lock:
    """Job lock util."""

    def __init__(self, identifier, timeout):
        """Init."""
        self.job_type = JobType.query.filter(JobType.job == identifier).first()
        self.timeout = timeout

    @property
    def _lock(self):
        """Get a lock."""
        return JobLock.query.filter(JobLock.job == self.job_type)

    def is_locked(self):
        """Check to see if a lock exists."""
        return self._lock.count() > 0

    def is_expired(self):
        """Check to see if a lock is expired."""
        if self.is_locked():
            prior_lock = self._lock.first()
            lock_datetime = prior_lock.lock_datetime.replace(tzinfo=timezone.utc)

            if lock_datetime < now() - timedelta(minutes=self.timeout):
                return True

        return False

    def create(self):
        """Create a new lock."""
        return JobLock.create(job=self.job_type, lock_datetime=now())

    def remove(self):
        """Remove a lock."""
        prior_lock = self._lock.first()
        return bool(prior_lock.delete())


class Job:
    """Base job."""

    identifier = "IDENTIFIER"
    lock_timeout = 10

    def __init__(self):
        """Init."""
        self.lock = Lock(self.identifier, self.lock_timeout)

    def run(self):
        """Run the job."""
        pass
