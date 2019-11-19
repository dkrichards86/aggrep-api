"""Tests for the utility module."""
from datetime import datetime
from unittest import TestCase

import jwt
import pytest

from aggrep.utils import (
    decode_token,
    encode_token,
    get_cache_key,
    now,
    overlap,
    slugify,
)


class TestUtils(TestCase):
    """Utility function tests."""

    def test_overlap(self):
        """Test overlap coefficient util."""
        assert overlap({"foo", "bar"}, {"foo", "bar"}) == 1
        assert overlap({"foo", "bar"}, {"foo", "baz"}) == 1 / 2
        assert overlap({"foo", "bar"}, {"foo", "bar", "baz"}) == 1
        assert overlap({"foo", "bar", "baz", "qux", "quux"}, {"quux"}) == 1
        assert overlap({"foo", "bar", "baz"}, {"qux", "quux"}) == 0
        assert overlap({"foo", "bar", "baz", "qux"}, {"quux"}) == 0

    def test_slugify(self):
        """Test sligification."""
        assert slugify("Test Slugify function") == "test-slugify-function"
        assert slugify("foobar") == "foobar"
        assert slugify(12345) == "12345"
        assert slugify(None) == "none"

    def test_decode_token(self):
        """Decode a JWT token."""
        time = now().timestamp()
        t1 = encode_token("k1", "v1", "secret", time=time)
        assert decode_token("k1", "secret", t1) == "v1"

        t2 = encode_token("k2", "v2", "secret", time=time - 1000)
        with pytest.raises(jwt.exceptions.ExpiredSignatureError):
            decode_token("k2", "secret", t2)

        t3 = encode_token("k3", "v3", "secret", time=time - 100, expires_in=10)
        with pytest.raises(jwt.exceptions.ExpiredSignatureError):
            decode_token("k3", "secret", t3)

        assert decode_token("k1", "secret", "iam.aninvalid.jsonwwebtoken") is None

    def test_encode_token(self):
        """Encode a JWT token."""
        time = datetime(2019, 9, 1).timestamp()
        expected = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJrZXkiOiJ2YWx1ZSIsImV4cCI6MTU2NzI5NjYwMC4wfQ.Lat3nCIYQQg6QeJxS9p76JuPQZn0yCtXx9FFAICXZrQ"  # noqa
        assert encode_token("key", "value", "secret", time=time) == expected

    def test_get_cache_key(self):
        """Test deterministic cache key generation."""
        k1 = get_cache_key("endpoint", "identity", 1, 10, "latest", route_arg=None)
        assert k1 == "endpoint_identity_1_10_latest"

        k2 = get_cache_key("endpoint", "identity", 2, 10, "popular", route_arg="arg")
        assert k2 == "endpoint_identity_2_10_popular_arg"

        k2 = get_cache_key("endpoint", None, 2, 10, "popular")
        assert k2 == "endpoint_anonymous_2_10_popular"
