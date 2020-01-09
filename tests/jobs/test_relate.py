"""Post relater unit tests."""
from collections import defaultdict

import pytest

from aggrep.jobs.relate import Relater


@pytest.mark.usefixtures("db")
class TestRelate:
    """Relater module tests."""

    def test_set_post_cache(self, category):
        """Test fetching the entity cache."""
        relater = Relater()

        relater.set_post_cache(category)
        assert type(relater.recent_posts) == dict
