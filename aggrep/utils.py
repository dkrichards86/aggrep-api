"""Aggregate Report utils."""

import re
import unicodedata
from datetime import datetime, timezone

import jwt


def overlap(s1, s2):
    """Determine similarity of two sets."""
    return len(s1 & s2) / min(len(s1), len(s2))


def now():
    """Get the current UTC time (timezone aware)."""
    return datetime.now(timezone.utc)


def slugify(value):
    """Convert a string to a slug."""
    value = str(value)
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def encode_token(key, value, secret, time=None, expires_in=600):
    """Encode a JWT."""
    if not time:
        time = now().timestamp()

    return jwt.encode(
        {key: value, "exp": time + expires_in}, secret, algorithm="HS256"
    ).decode("utf-8")


def decode_token(key, secret, token):
    """Decode a JWT."""
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])[key]
    except jwt.DecodeError:
        return None


def get_cache_key(endpoint, identity, page, per_page, sort, route_arg=None):
    """Build a cache key for the endpoint."""
    if not identity:
        identity = "anonymous"

    cache_key = "{}_{}_{}_{}_{}".format(endpoint, identity, page, per_page, sort)
    if route_arg:
        cache_key = "{}_{}".format(cache_key, route_arg)

    return cache_key
