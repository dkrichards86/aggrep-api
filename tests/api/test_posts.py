"""Post module unit tests."""
from datetime import timedelta
from random import randint

import pytest

from aggrep.api.posts import (
    filter_user_categories,
    filter_user_sources,
    get_all_posts,
    get_posts_by_category,
    get_posts_by_search,
    get_posts_by_source,
    get_similar_posts,
    limit_posts,
    sort_posts,
)
from aggrep.constants import LATEST, POPULAR
from aggrep.models import Category, Feed, Post, Similarity, Source
from aggrep.utils import build_search_query, now
from tests.factories import PostFactory


@pytest.mark.usefixtures("db")
class TestPosts:
    """Test posts module."""

    def test_get_all_posts(self, app):
        """Test get all posts."""
        n_out_of_bounds = 0
        for instance in PostFactory.create_batch(25):
            if instance.id % 5 == 0:
                delta = now() - timedelta(days=15)
                instance.update(published_datetime=delta)
                n_out_of_bounds += 1
            instance.save()

        posts = get_all_posts()
        assert posts.count() == 25 - n_out_of_bounds

    def test_get_posts_by_source(self, app):
        """Test getting posts by source."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        posts = get_posts_by_source(cat)

        assert posts.count() == 5

    def test_get_posts_by_category(self, app):
        """Test getting posts by category."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        posts = get_posts_by_category(cat)

        assert posts.count() == 5

    def test_get_posts_by_search(self, app):
        """Test getting posts by a search term."""
        posts = [
            "Jived fox nymph grabs quick waltz.",
            "Glib jocks quiz nymph to vex dwarf.",
            "Sphinx of black quartz, judge my vow.",
            "How vexingly quick daft zebras jump.",
            "Jackdaws love my big sphinx of quartz.",
        ]

        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, post in enumerate(posts):
            Post.create(
                feed=feed, title=post, desc=post, link="link{}.com".format(i)
            )

        assert get_posts_by_search(build_search_query("nymph")).count() == 2
        assert get_posts_by_search(build_search_query("nymph dwarf")).count() == 1
        assert get_posts_by_search(build_search_query("quartz")).count() == 2

    def test_get_similar_posts(self, app):
        """Test getting similar posts."""
        posts = []
        for instance in PostFactory.create_batch(5):
            posts.append(instance)
            instance.save()

        Similarity.create(source_id=posts[0].id, related_id=posts[2].id)
        Similarity.create(source_id=posts[0].id, related_id=posts[3].id)
        Similarity.create(source_id=posts[0].id, related_id=posts[4].id)
        Similarity.create(source_id=posts[1].id, related_id=posts[0].id)
        Similarity.create(source_id=posts[1].id, related_id=posts[2].id)
        Similarity.create(source_id=posts[2].id, related_id=posts[1].id)

        # Each post returns itself and all of its similar posts.
        assert get_similar_posts(posts[0].uid).count() == 4
        assert get_similar_posts(posts[1].uid).count() == 3
        assert get_similar_posts(posts[2].uid).count() == 2

    def test_filter_user_categories(self, app, user):
        """Test getting posts filtered by user prefs."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 10 == 0:
                instance.update(feed=feed)
            instance.save()

        user.excluded_categories = [cat]
        user.save()

        posts = filter_user_categories(get_all_posts(), user)
        assert posts.count() == 22  # 25 posts - 3 excludes

    def test_filter_user_sources(self, app, user):
        """Test getting posts filtered by user prefs."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.update(feed=feed)
            instance.save()

        user.excluded_sources = [src]
        user.save()

        posts = filter_user_sources(get_all_posts(), user)
        assert posts.count() == 20  # 25 posts - 5 excludes

    def test_limit_posts(self, app):
        """Test limiting posts to n most recent."""
        for instance in PostFactory.create_batch(25):
            instance.save()

        posts = limit_posts(get_all_posts(), limit=5)
        assert posts.count() == 5

    def test_sort_posts(self, app):
        """Test sorting posts."""
        for instance in PostFactory.create_batch(20):
            clicks = 0
            impressions = 0
            ctr = 0
            if instance.id % 5 == 0:
                clicks = randint(1, 2)
                impressions = randint(1, 5)
                ctr = clicks / impressions
            instance.actions.update(clicks=clicks, impressions=impressions, ctr=ctr)
            instance.save()

        posts = get_all_posts()
        assert sort_posts(posts, POPULAR).count() == sort_posts(posts, LATEST).count()

        popular_post_ids = [p.id for p in sort_posts(posts, POPULAR).all()]
        latest_post_ids = [p.id for p in sort_posts(posts, LATEST).all()]
        assert popular_post_ids != latest_post_ids
