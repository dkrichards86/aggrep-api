"""Factories to help in tests."""

from datetime import datetime, timezone

from factory import Factory, PostGenerationMethodCall, Sequence, SubFactory, fuzzy

from aggrep.models import Category, Feed, Post, Source, User


class CategoryFactory(Factory):
    """Category model factory."""

    class Meta:
        """Factory metadata."""

        model = Category

    id = Sequence(lambda n: n)
    slug = Sequence(lambda n: "category-{0}".format(n))
    title = Sequence(lambda n: "Category {0}".format(n))


class SourceFactory(Factory):
    """Source model factory."""

    class Meta:
        """Factory metadata."""

        model = Source

    id = Sequence(lambda n: n)
    slug = Sequence(lambda n: "category-{0}".format(n))
    title = Sequence(lambda n: "Category {0}".format(n))


class FeedFactory(Factory):
    """Feed model factory."""

    class Meta:
        """Factory metadata."""

        model = Feed

    id = Sequence(lambda n: n)
    url = Sequence(lambda n: "{0}.feed.com".format(n))
    source = SubFactory(SourceFactory)
    category = SubFactory(CategoryFactory)


class PostFactory(Factory):
    """Post model factory."""

    class Meta:
        """Factory metadata."""

        model = Post

    id = Sequence(lambda n: n)
    title = Sequence(lambda n: "Post {0}".format(n))
    desc = fuzzy.FuzzyText()
    link = Sequence(lambda n: "{0}.post.com".format(n))
    published_datetime = fuzzy.FuzzyDateTime(
        datetime(2019, 10, 10, tzinfo=timezone.utc)
    )
    ingested_datetime = fuzzy.FuzzyDateTime(datetime(2019, 10, 10, tzinfo=timezone.utc))

    feed = SubFactory(FeedFactory)


class UserFactory(Factory):
    """User model factory."""

    class Meta:
        """Factory metadata."""

        model = User

    id = Sequence(lambda n: n)
    email = Sequence(lambda n: "user{0}@example.com".format(n))
    password = PostGenerationMethodCall("set_password", "example")
    active = True
