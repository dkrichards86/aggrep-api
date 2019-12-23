"""Post processing unit tests."""
from datetime import timedelta

import pytest

from aggrep.jobs.process import Processor, clean, extract
from aggrep.models import EntityProcessQueue, JobLock, JobType
from aggrep.utils import now
from tests.factories import PostFactory

BASE_TEXT = """
Topless female activists on Sunday interrupted a demonstration in Madrid commemorating the legacy of
Spain’s former dictator Francisco Franco, 44 years after his death. Chanting \"for fascism no honor
and no glory,\" half a dozen women from feminist group Femen, with the same slogan emblazoned across
their chests, burst into the crowd when it reached Madrid’s Plaza de Oriente. They were quickly
removed by police. Hundreds of Franco supporters turned out for the march, which is held around Nov.
20 every year to mark the anniversary of the dictator’s death. Some demonstrators carried flags with
Francoist icons and held an arm aloft in the fascist salute.
"""


@pytest.mark.usefixtures("db")
class TestProcess:
    """Processing module tests."""

    def test_extract(self):
        """Test entity extraction."""

        result = extract(BASE_TEXT)
        expected = set(["franco", "de", "francisco", "femen", "oriente", "madrid", "plaza"])
        assert result == expected

    def test_clean(self):
        """Test text cleaning util."""

        c1 = clean("Jived fox nymph grabs quick waltz.")
        e1 = "Jived fox nymph grabs quick waltz."
        assert c1 == e1

        c2 = clean("Glib jocks quiz nymph to vex dwarf.   ")
        e2 = "Glib jocks quiz nymph to vex dwarf."
        assert c2 == e2

        c3 = clean("Sphinx of black   quartz, judge my vow.")
        e3 = "Sphinx of black quartz, judge my vow."
        assert c3 == e3

        c4 = clean("How vexingly quick\ndaft zebras jump.")
        e4 = "How vexingly quick daft zebras jump."
        assert c4 == e4

        c5 = clean("  The five boxing wizards jump quickly.")
        e5 = "The five boxing wizards jump quickly."
        assert c5 == e5

        c6 = clean("\tJackdaws love my big sphinx of quartz.\t")
        e6 = "Jackdaws love my big sphinx of quartz."
        assert c6 == e6

        c7 = clean("Pack my box with five dozen liquor jugs\U0001F600.")
        e7 = "Pack my box with five dozen liquor jugs."
        assert c7 == e7

    def test_process_entities(self):
        """Test processing."""
        processor = Processor()

        for instance in PostFactory.create_batch(20):
            instance.save()
            EntityProcessQueue.create(post_id=instance.id)

        processor.run()

        assert EntityProcessQueue.query.count() == 0
        job_type = JobType.query.filter(JobType.job == "PROCESS").first()
        assert JobLock.query.filter(JobLock.job == job_type).first() is None

    def test_process_entities_no_posts(self):
        """Test processing with no posts."""
        processor = Processor()
        processor.run()

        assert EntityProcessQueue.query.count() == 0
        job_type = JobType.query.filter(JobType.job == "PROCESS").first()
        assert JobLock.query.filter(JobLock.job == job_type).first() is None

    def test_process_entities_prior_lock(self):
        """Test processing with existing lock."""
        processor = Processor()

        for instance in PostFactory.create_batch(20):
            instance.save()
            EntityProcessQueue.create(post_id=instance.id)

        job_type = JobType.query.filter(JobType.job == "PROCESS").first()
        JobLock.create(job=job_type)

        processor.run()

        assert EntityProcessQueue.query.count() == 20
        assert JobLock.query.filter(JobLock.job == job_type).first() is not None

    def test_process_entities_expired_lock(self):
        """Test processing with expired lock."""
        processor = Processor()

        for instance in PostFactory.create_batch(20):
            instance.save()
            EntityProcessQueue.create(post_id=instance.id)

        job_type = JobType.query.filter(JobType.job == "PROCESS").first()
        JobLock.create(job=job_type, lock_datetime=now() - timedelta(minutes=10))

        processor.run()

        assert EntityProcessQueue.query.count() == 0
        assert JobLock.query.filter(JobLock.job == job_type).first() is None
