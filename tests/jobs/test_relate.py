"""Post relater unit tests."""
from collections import defaultdict

import pytest

from aggrep.jobs.relate import Relater


@pytest.mark.usefixtures("db")
class TestRelate:
    """Relater module tests."""

    def test_get_entity_cache(self, category):
        """Test fetching the entity cache."""
        relater = Relater()

        relater.set_entity_cache(category)
        assert type(relater.entity_cache) == defaultdict
