"""Model unit tests."""
from unittest import mock

import pytest
from flask_jwt_extended import create_access_token

from aggrep.models import Bookmark, Category, Feed, Post, PostAction, PostView, Source
from tests.factories import CategoryFactory, PostFactory, SourceFactory


@pytest.mark.usefixtures("db")
class TestFollowRedirect:
    """Test the click follower endpoint."""

    def test_endpoint(self, app, client, post):
        """Test a successful request."""

        instance = PostFactory()
        instance.save()

        url = "/{}".format(instance.uid)
        rv = client.get(url)
        assert rv.status_code == 302

    @mock.patch("aggrep.api.views.register_click")
    def test_endpoint_click(self, mock_click, app, client, post):
        """Test a successful request."""

        instance = PostFactory()
        instance.save()

        url = "/{}".format(instance.uid)
        client.get(url)
        assert mock_click.call_count == 1


@pytest.mark.usefixtures("db")
class TestAllPosts:
    """Test all posts endpoint."""

    def test_endpoint_defaults(self, app, client):
        """Test a successful request."""

        for instance in PostFactory.create_batch(25):
            instance.save()

        rv = client.get("/v1/posts")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts"
        assert len(json_data["items"]) == 20
        assert json_data["page"] == 1
        assert json_data["per_page"] == 20
        assert json_data["total_pages"] == 2
        assert json_data["total_items"] == 25

    def test_endpoint_sort(self, app, client):
        """Test a successful request with sort argument."""
        for instance in PostFactory.create_batch(25):
            instance.save()

        rv = client.get("/v1/posts?sort=latest")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Latest Posts"
        assert len(json_data["items"]) == 20
        assert json_data["page"] == 1
        assert json_data["per_page"] == 20
        assert json_data["total_pages"] == 2
        assert json_data["total_items"] == 25

    def test_endpoint_per_page(self, app, client):
        """Test a successful request with per_page argument."""
        for instance in PostFactory.create_batch(25):
            instance.save()

        rv = client.get("/v1/posts?per_page=10")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts"
        assert len(json_data["items"]) == 10
        assert json_data["page"] == 1
        assert json_data["per_page"] == 10
        assert json_data["total_pages"] == 3
        assert json_data["total_items"] == 25

    def test_endpoint_page(self, app, client):
        """Test a successful request with oagr argument."""
        for instance in PostFactory.create_batch(25):
            instance.save()

        rv = client.get("/v1/posts?page=2")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts"
        assert len(json_data["items"]) == 5
        assert json_data["page"] == 2
        assert json_data["per_page"] == 20
        assert json_data["total_pages"] == 2
        assert json_data["total_items"] == 25

    def test_endpoint_user_excludes(self, app, client, user):
        """Test a successful request."""
        excluded_sources = []
        excluded_categories = []
        for instance in PostFactory.create_batch(25):
            if instance.id % 10 == 0:
                # Pick 2 categories to exclude.
                excluded_categories.append(instance.feed.category)
            elif instance.id % 5 == 0:
                # Pick 3 sources to exclude.
                excluded_sources.append(instance.feed.source)
            instance.save()

        user.excluded_sources = excluded_sources
        user.excluded_categories = excluded_categories
        user.save()

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.get("/v1/posts", headers={"Authorization": token})

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts"
        assert len(json_data["items"]) == 20
        assert json_data["page"] == 1
        assert json_data["per_page"] == 20
        assert json_data["total_pages"] == 1
        assert json_data["total_items"] == 20

    @mock.patch("aggrep.api.views.register_impression")
    def test_endpoint_impressions(self, mock_impression, app, client):
        """Test a successful request."""

        for instance in PostFactory.create_batch(20):
            instance.save()

        rv = client.get("/v1/posts")

        assert rv.status_code == 200
        assert mock_impression.call_count == 20


@pytest.mark.usefixtures("db")
class TestSourcePosts:
    """Test source posts endpoint."""

    def test_endpoint_defaults(self, app, client):
        """Test a successful request."""

        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        rv = client.get("/v1/source/source")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts by Test Source"
        assert len(json_data["items"]) == 5
        assert json_data["page"] == 1
        assert json_data["per_page"] == 20
        assert json_data["total_pages"] == 1
        assert json_data["total_items"] == 5

    def test_source_doesnt_exist(self, app, client):
        """Test invalid source."""
        rv = client.get("/v1/source/doesnt-exist")

        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Source 'doesnt-exist' does not exist."

    def test_endpoint_sort(self, app, client):
        """Test a successful request with sort argument."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        rv = client.get("/v1/source/source?sort=latest")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Latest Posts by Test Source"
        assert len(json_data["items"]) == 5
        assert json_data["page"] == 1
        assert json_data["per_page"] == 20
        assert json_data["total_pages"] == 1
        assert json_data["total_items"] == 5

    def test_endpoint_per_page(self, app, client):
        """Test a successful request with per_page argument."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        rv = client.get("/v1/source/source?per_page=2")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts by Test Source"
        assert len(json_data["items"]) == 2
        assert json_data["page"] == 1
        assert json_data["per_page"] == 2
        assert json_data["total_pages"] == 3
        assert json_data["total_items"] == 5

    def test_endpoint_page(self, app, client):
        """Test a successful request with oagr argument."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        rv = client.get("/v1/source/source?per_page=2&page=2")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts by Test Source"
        assert len(json_data["items"]) == 2
        assert json_data["page"] == 2
        assert json_data["per_page"] == 2
        assert json_data["total_pages"] == 3
        assert json_data["total_items"] == 5


@pytest.mark.usefixtures("db")
class TestCategoryPosts:
    """Test category posts endpoint."""

    def test_endpoint_defaults(self, app, client):
        """Test a successful request."""

        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        rv = client.get("/v1/category/category")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts in Test Category"
        assert len(json_data["items"]) == 5
        assert json_data["page"] == 1
        assert json_data["per_page"] == 20
        assert json_data["total_pages"] == 1
        assert json_data["total_items"] == 5

    def test_category_doesnt_exist(self, app, client):
        """Test invalid category."""
        rv = client.get("/v1/category/doesnt-exist")

        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Category 'doesnt-exist' does not exist."

    def test_endpoint_sort(self, app, client):
        """Test a successful request with sort argument."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        rv = client.get("/v1/category/category?sort=latest")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Latest Posts in Test Category"
        assert len(json_data["items"]) == 5
        assert json_data["page"] == 1
        assert json_data["per_page"] == 20
        assert json_data["total_pages"] == 1
        assert json_data["total_items"] == 5

    def test_endpoint_per_page(self, app, client):
        """Test a successful request with per_page argument."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        rv = client.get("/v1/category/category?per_page=2")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts in Test Category"
        assert len(json_data["items"]) == 2
        assert json_data["page"] == 1
        assert json_data["per_page"] == 2
        assert json_data["total_pages"] == 3
        assert json_data["total_items"] == 5

    def test_endpoint_page(self, app, client):
        """Test a successful request with oagr argument."""
        src = Source.create(slug="source", title="Test Source")
        cat = Category.create(slug="category", title="Test Category")
        feed = Feed.create(source=src, category=cat, url="feed.com")

        for i, instance in enumerate(PostFactory.create_batch(25)):
            if i % 5 == 0:
                instance.feed = feed
            instance.save()

        rv = client.get("/v1/category/category?per_page=2&page=2")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Popular Posts in Test Category"
        assert len(json_data["items"]) == 2
        assert json_data["page"] == 2
        assert json_data["per_page"] == 2
        assert json_data["total_pages"] == 3
        assert json_data["total_items"] == 5


@pytest.mark.usefixtures("db")
class TestSearch:
    """Test search endpoint."""

    def test_endpoint(self, app, client, feed):
        """Test a successful request."""

        posts = [
            "Jived fox nymph grabs quick waltz.",
            "Glib jocks quiz nymph to vex dwarf.",
            "Sphinx of black quartz, judge my vow.",
            "How vexingly quick daft zebras jump.",
            "Jackdaws love my big sphinx of quartz.",
        ]

        for i, post in enumerate(posts):
            p = Post.create(
                feed=feed, title=post, desc=post, link="link{}.com".format(i)
            )
            PostAction.create(post_id=p.id, clicks=0, impressions=0, ctr=0)

        rv = client.get("/v1/search?query=nymph")
        json_data = rv.get_json()
        assert json_data["total_items"] == 2

        rv = client.get("/v1/search?query=nymph dwarf")
        json_data = rv.get_json()
        assert json_data["total_items"] == 1

        rv = client.get("/v1/search?query=quartz")
        json_data = rv.get_json()
        assert json_data["total_items"] == 2

    def test_missing_term(self, app, client, feed):
        """Test a missing search term."""
        rv = client.get("/v1/search")
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "No search terms provided."


@pytest.mark.usefixtures("db")
class TestSimilar:
    """Test similar posts endpoint."""

    def test_endpoint(self, app, client):
        """Test a successful request."""

        posts = []
        for instance in PostFactory.create_batch(5):
            posts.append(instance)
            instance.save()

        rv = client.get("/v1/similar/{}".format(posts[0].uid))
        assert rv.status_code == 200


@pytest.mark.usefixtures("db")
class TestBookmarkedPosts:
    """Test bookmarked posts endpoint."""

    def test_endpoint(self, app, user, client):
        """Test a successful request."""

        for i, instance in enumerate(PostFactory.create_batch(25)):
            instance.save()
            if i % 5 == 0:
                Bookmark.create(user_id=user.id, post_id=instance.id)

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.get("/v1/bookmarks", headers={"Authorization": token})

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Bookmarked Posts"
        assert len(json_data["items"]) == 5
        assert json_data["page"] == 1
        assert json_data["per_page"] == 20
        assert json_data["total_pages"] == 1
        assert json_data["total_items"] == 5

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        rv = client.get("/v1/bookmarks")
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"


@pytest.mark.usefixtures("db")
class TestBookmarkedIDs:
    """Test bookmark IDs endpoint."""

    def test_endpoint(self, app, user, client):
        """Test a successful request."""

        for i, instance in enumerate(PostFactory.create_batch(25)):
            instance.save()
            if i % 5 == 0:
                Bookmark.create(user_id=user.id, post_id=instance.id)

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.get("/v1/bookmarks/ids", headers={"Authorization": token})

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert len(json_data["bookmarks"]) == 5

    def test_post_view(self, app, post, user, client):
        """Test a successful POST request."""

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

            rv = client.post(
                "/v1/bookmarks/ids",
                json=dict(uid=post.uid),
                headers={"Authorization": token},
            )

            assert rv.status_code == 200
            json_data = rv.get_json()
            assert json_data["msg"] == "Bookmark saved!"
            assert len(json_data["bookmarks"]) == 1
            assert user.bookmarks.count() == 1

    def test_post_view_no_uid(self, app, post, user, client):
        """Test an unsuccessful POST request."""

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

            Bookmark.create(user_id=user.id, post_id=post.id)

            rv = client.post(
                "/v1/bookmarks/ids", json=dict(), headers={"Authorization": token}
            )

            assert rv.status_code == 400

    def test_post_view_invalid_uid(self, app, post, user, client):
        """Test an unsuccessful POST request."""

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

            rv = client.post(
                "/v1/bookmarks/ids",
                json=dict(uid="mmmmmm"),
                headers={"Authorization": token},
            )

            assert rv.status_code == 400

    def test_post_view_duplicate_id(self, app, post, user, client):
        """Test a successful POST request."""

        with app.app_context():
            Bookmark.create(user_id=user.id, post_id=post.id)
            token = "Bearer {}".format(create_access_token(user.email))

            rv = client.post(
                "/v1/bookmarks/ids",
                json=dict(uid=post.uid),
                headers={"Authorization": token},
            )

            assert rv.status_code == 200
            json_data = rv.get_json()
            assert len(json_data["bookmarks"]) == 1
            assert user.bookmarks.count() == 1

    def test_delete_view(self, app, post, user, client):
        """Test a successful DELETE request."""

        with app.app_context():
            Bookmark.create(user_id=user.id, post_id=post.id)
            token = "Bearer {}".format(create_access_token(user.email))

            rv = client.delete(
                "/v1/bookmarks/ids",
                json=dict(uid=post.uid),
                headers={"Authorization": token},
            )

            assert rv.status_code == 200
            json_data = rv.get_json()
            assert json_data["msg"] == "Bookmark removed!"
            assert len(json_data["bookmarks"]) == 0
            assert user.bookmarks.count() == 0

    def test_delete_view_no_uid(self, app, post, user, client):
        """Test an unsuccessful DELETE request."""

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

            Bookmark.create(user_id=user.id, post_id=post.id)

            rv = client.delete(
                "/v1/bookmarks/ids", json=dict(), headers={"Authorization": token}
            )

            assert rv.status_code == 400

    def test_delete_view_invalid_uid(self, app, post, user, client):
        """Test an unsuccessful DELETE request."""

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

            rv = client.delete(
                "/v1/bookmarks/ids",
                json=dict(uid="mmmmmm"),
                headers={"Authorization": token},
            )

            assert rv.status_code == 400

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        rv = client.get("/v1/bookmarks/ids")
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"


@pytest.mark.usefixtures("db")
class TestViewedPosts:
    """Test viewed posts endpoint."""

    def test_endpoint(self, app, user, client):
        """Test a successful request."""

        for i, instance in enumerate(PostFactory.create_batch(25)):
            instance.save()
            if i % 5 == 0:
                PostView.create(user_id=user.id, post_id=instance.id)

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.get("/v1/views", headers={"Authorization": token})

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert json_data["title"] == "Recently Viewed Posts"
        assert len(json_data["items"]) == 5
        assert json_data["page"] == 1
        assert json_data["per_page"] == 10
        assert json_data["total_pages"] == 1
        assert json_data["total_items"] == 5

    def test_post_view(self, app, post, user, client):
        """Test a successful POST request."""

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

            rv = client.post(
                "/v1/views", json=dict(uid=post.uid), headers={"Authorization": token}
            )

            assert rv.status_code == 200
            assert user.post_views.count() == 1

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        rv = client.get("/v1/views")
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"


@pytest.mark.usefixtures("db")
class TestSources:
    """Test sources endpoint."""

    def test_endpoint(self, app, client):
        """Test a successful request."""

        for instance in SourceFactory.create_batch(25):
            instance.save()

        rv = client.get("/v1/sources")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert len(json_data["sources"]) == 25


@pytest.mark.usefixtures("db")
class TestCategories:
    """Test categories endpoint."""

    def test_endpoint(self, app, client):
        """Test a successful request."""

        for instance in CategoryFactory.create_batch(8):
            instance.save()

        rv = client.get("/v1/categories")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert len(json_data["categories"]) == 8


@pytest.mark.usefixtures("db")
class TestManageCategories:
    """Test manage categories endpoint."""

    def test_endpoint_get(self, app, client, user):
        """Test a successful request."""

        included_category_ids = []
        excluded_category_ids = []
        for i, instance in enumerate(CategoryFactory.create_batch(5)):
            if i == 0:
                excluded_category_ids.append(instance.id)
            else:
                included_category_ids.append(instance.id)
            instance.save()

        user.excluded_categories = Category.query.filter(
            Category.id.in_(excluded_category_ids)
        ).all()
        user.save()

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.get("/v1/manage/categories", headers={"Authorization": token})

        assert rv.status_code == 200
        json_data = rv.get_json()
        assert len(json_data["included_categories"]) == len(included_category_ids)
        assert sorted(json_data["included_categories"]) == sorted(included_category_ids)
        assert len(json_data["excluded_categories"]) == len(excluded_category_ids)
        assert sorted(json_data["excluded_categories"]) == sorted(excluded_category_ids)

    def test_endpoint_post(self, app, client, user):
        """Test a successful request."""

        included_category_ids = []
        excluded_category_ids = []
        for i, instance in enumerate(CategoryFactory.create_batch(5)):
            if i == 0:
                excluded_category_ids.append(instance.id)
            else:
                included_category_ids.append(instance.id)
            instance.save()

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        payload = dict(excluded_categories=excluded_category_ids)
        rv = client.post(
            "/v1/manage/categories", json=payload, headers={"Authorization": token}
        )

        assert rv.status_code == 200
        json_data = rv.get_json()
        assert len(json_data["included_categories"]) == len(included_category_ids)
        assert sorted(json_data["included_categories"]) == sorted(included_category_ids)
        assert len(json_data["excluded_categories"]) == len(excluded_category_ids)
        assert sorted(json_data["excluded_categories"]) == sorted(excluded_category_ids)

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        rv = client.get("/v1/manage/categories")
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"


@pytest.mark.usefixtures("db")
class TestManageSources:
    """Test manage sources endpoint."""

    def test_endpoint_get(self, app, client, user):
        """Test a successful request."""

        included_source_ids = []
        excluded_source_ids = []
        for i, instance in enumerate(SourceFactory.create_batch(5)):
            if i == 0:
                excluded_source_ids.append(instance.id)
            else:
                included_source_ids.append(instance.id)
            instance.save()

        user.excluded_sources = Source.query.filter(
            Source.id.in_(excluded_source_ids)
        ).all()
        user.save()

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.get("/v1/manage/sources", headers={"Authorization": token})

        assert rv.status_code == 200
        json_data = rv.get_json()
        assert len(json_data["included_sources"]) == len(included_source_ids)
        assert sorted(json_data["included_sources"]) == sorted(included_source_ids)
        assert len(json_data["excluded_sources"]) == len(excluded_source_ids)
        assert sorted(json_data["excluded_sources"]) == sorted(excluded_source_ids)

    def test_endpoint_post(self, app, client, user):
        """Test a successful request."""

        included_source_ids = []
        excluded_source_ids = []
        for i, instance in enumerate(SourceFactory.create_batch(5)):
            if i == 0:
                excluded_source_ids.append(instance.id)
            else:
                included_source_ids.append(instance.id)
            instance.save()

        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        payload = dict(excluded_sources=excluded_source_ids)
        rv = client.post(
            "/v1/manage/sources", json=payload, headers={"Authorization": token}
        )

        assert rv.status_code == 200
        json_data = rv.get_json()
        assert len(json_data["included_sources"]) == len(included_source_ids)
        assert sorted(json_data["included_sources"]) == sorted(included_source_ids)
        assert len(json_data["excluded_sources"]) == len(excluded_source_ids)
        assert sorted(json_data["excluded_sources"]) == sorted(excluded_source_ids)

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        rv = client.get("/v1/manage/sources")
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"


@pytest.mark.usefixtures("db")
class TestAuthTokenConfirm:
    """Test the auth token confirmation endpoint."""

    def test_endpoint(self, app, client, user):
        """Test a successful request."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.get("/v1/auth/token/confirm", headers={"Authorization": token})
        assert rv.status_code == 200
        json_data = rv.get_json()
        assert json_data["msg"] == "Token verification successful!"
        assert "access_token" in json_data
        assert "user" in json_data

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        rv = client.get("/v1/auth/token/confirm")
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.post("/v1/auth/token/confirm")
        assert rv.status_code == 405


@pytest.mark.usefixtures("db")
class TestAuthLogin:
    """Test the login endpoint."""

    def test_endpoint(self, app, client, user):
        """Test a successful request."""
        rv = client.post(
            "/v1/auth/login", json=dict(email=user.email, password="foobar")
        )
        assert rv.status_code == 200
        json_data = rv.get_json()
        assert json_data["msg"] == "Login Successful"
        assert "access_token" in json_data
        assert "user" in json_data

    def test_incorrect_email(self, app, client, user):
        """Test a request with an incorrect email."""
        rv = client.post(
            "/v1/auth/login", json=dict(email="foo@bar.com", password="foobar")
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid email address or password"

    def test_incorrect_password(self, app, client, user):
        """Test a request with an incorrect password."""
        rv = client.post(
            "/v1/auth/login", json=dict(email="foo@bar.com", password="foobaz")
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid email address or password"

    def test_missing_email(self, app, client, user):
        """Test a request with no email."""
        rv = client.post("/v1/auth/login", json=dict(password="foobar"))
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete login."

    def test_missing_password(self, app, client, user):
        """Test a request with no password."""
        rv = client.post("/v1/auth/login", json=dict(email=user.email))
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete login."

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.get("/v1/auth/login")
        assert rv.status_code == 405

    def test_already_logged_in(self, app, client, user):
        """Test a request with a logged in user."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post("/v1/auth/login", headers={"Authorization": token})
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "You are already logged in."

    def test_bad_request(self, app, client, user):
        """Test a request with no body."""
        rv = client.post("/v1/auth/login")
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid request."


@pytest.mark.usefixtures("db")
class TestAuthRegister:
    """Test the registration endpoint."""

    @mock.patch("aggrep.api.views.send_email")
    def test_endpoint(self, mock_email, app, client):
        """Test a successful request."""
        payload = dict(
            email="foo@bar.com", password="foobar", password_confirm="foobar"
        )
        rv = client.post("/v1/auth/register", json=payload)
        assert rv.status_code == 200
        json_data = rv.get_json()
        assert json_data["msg"] == "Registration Successful!"
        assert "access_token" in json_data
        assert "user" in json_data
        assert mock_email.called_once

    def test_different_passwords(self, app, client):
        """Test a request with no email."""
        payload = dict(
            email="foo@bar.com", password="foobar", password_confirm="foobaz"
        )
        rv = client.post("/v1/auth/register", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete registration."

    def test_missing_email(self, app, client):
        """Test a request with no email."""
        payload = dict(password="foobar", password_confirm="foobar")
        rv = client.post("/v1/auth/register", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete registration."

    def test_missing_password(self, app, client, user):
        """Test a request with no password."""
        payload = dict(email="foo@bar.com", password_confirm="foobar")
        rv = client.post("/v1/auth/register", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete registration."

    def test_missing_password_confirm(self, app, client, user):
        """Test a request with no password."""
        payload = dict(email="foo@bar.com", password="foobar")
        rv = client.post("/v1/auth/register", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete registration."

    def test_already_logged_in(self, app, client, user):
        """Test a request with a logged in user."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post("/v1/auth/register", headers={"Authorization": token})
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "You are already registered."

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.get("/v1/auth/register")
        assert rv.status_code == 405

    def test_bad_request(self, app, client, user):
        """Test a request with no body."""
        rv = client.post("/v1/auth/login")
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid request."


@pytest.mark.usefixtures("db")
class TestAuthEmailUpdate:
    """Test the email update endpoint."""

    @mock.patch("aggrep.api.views.send_email")
    def test_endpoint(self, mock_email, app, client, user):
        """Test a successful request."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        payload = dict(email="foo@bar.com")
        rv = client.post(
            "/v1/auth/email/update", json=payload, headers={"Authorization": token}
        )
        assert rv.status_code == 200
        json_data = rv.get_json()
        msg = "Your email has been updated. Please check your email for a confirmation link."
        assert json_data["msg"] == msg
        assert "access_token" in json_data["auth"]
        assert "user" in json_data["auth"]
        assert mock_email.called_once

    def test_missing_email(self, app, client, user):
        """Test a request with no email."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post(
            "/v1/auth/email/update", json=dict(), headers={"Authorization": token}
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to update email."

    def test_email_already_exists(self, app, client, user):
        """Test a request with a used email."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        payload = dict(email=user.email)
        rv = client.post(
            "/v1/auth/email/update", json=payload, headers={"Authorization": token}
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to update email."

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.get("/v1/auth/email/update")
        assert rv.status_code == 405

    def test_bad_request(self, app, client, user):
        """Test a request with no body."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post("/v1/auth/email/update", headers={"Authorization": token})
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid request."

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        payload = dict(email="foo@bar.com")
        rv = client.post("/v1/auth/email/update", json=payload)
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"


@pytest.mark.usefixtures("db")
class TestAuthEmailConfirmRequest:
    """Test the email confirmation request endpoint."""

    @mock.patch("aggrep.api.views.send_email")
    def test_endpoint(self, mock_email, app, client, user):
        """Test a successful request."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post(
            "/v1/auth/email/confirm/request",
            json=dict(),
            headers={"Authorization": token},
        )
        assert rv.status_code == 200
        json_data = rv.get_json()
        msg = "A confirmation email has been sent to your email address."
        assert json_data["msg"] == msg
        assert mock_email.called_once

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.get("/v1/auth/email/confirm/request")
        assert rv.status_code == 405

    def test_bad_request(self, app, client, user):
        """Test a request with no body."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post(
            "/v1/auth/email/confirm/request", headers={"Authorization": token}
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid request."

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        payload = dict(email="foo@bar.com")
        rv = client.post("/v1/auth/email/confirm/request", json=payload)
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"


@pytest.mark.usefixtures("db")
class TestAuthEmailConfirmToken:
    """Test the email confirmation request endpoint."""

    def test_endpoint(self, app, client, user):
        """Test a successful request."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))
            reset_token = user.get_email_confirm_token()

        payload = dict(token=reset_token)
        rv = client.post(
            "/v1/auth/email/confirm/token",
            json=payload,
            headers={"Authorization": token},
        )
        assert rv.status_code == 200
        json_data = rv.get_json()
        assert json_data["msg"] == "Your email address has been confirmed."

    def test_endpoint_bad_token(self, app, client, user):
        """Test a request with a bad token."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))
            reset_token = "THIS.SHOULDNT.WORK"

        payload = dict(token=reset_token)
        rv = client.post(
            "/v1/auth/email/confirm/token",
            json=payload,
            headers={"Authorization": token},
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Confirmation token is invalid."

    def test_endpoint_bad_payload(self, app, client, user):
        """Test a request with a bad payload."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        payload = dict()
        rv = client.post(
            "/v1/auth/email/confirm/token",
            json=payload,
            headers={"Authorization": token},
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to verify the email account."

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.get("/v1/auth/email/confirm/token")
        assert rv.status_code == 405

    def test_bad_request(self, app, client, user):
        """Test a request with no body."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post(
            "/v1/auth/email/confirm/token", headers={"Authorization": token}
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid request."


@pytest.mark.usefixtures("db")
class TestAuthPasswordUpdate:
    """Test the password update endpoint."""

    @mock.patch("aggrep.api.views.send_email")
    def test_endpoint(self, mock_email, app, client, user):
        """Test a successful request."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        user.set_password("password")
        payload = dict(
            curr_password="password", new_password="foobar", password_confirm="foobar"
        )
        rv = client.post(
            "/v1/auth/password/update", json=payload, headers={"Authorization": token}
        )
        assert rv.status_code == 200
        json_data = rv.get_json()
        assert json_data["msg"] == "Your password has been updated."
        assert mock_email.called_once

    def test_endpoint_incorrect_password(self, app, client, user):
        """Test a request with a missing token."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        payload = dict(
            curr_password="password", new_password="foobar", password_confirm="foobar"
        )
        rv = client.post(
            "/v1/auth/password/update", json=payload, headers={"Authorization": token}
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Password incorrect."

    def test_endpoint_no_curr_pass(self, app, client, user):
        """Test a request with a missing token."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        payload = dict(new_password="foobar", password_confirm="foobar")
        rv = client.post(
            "/v1/auth/password/update", json=payload, headers={"Authorization": token}
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to update your password."

    def test_endpoint_no_password(self, app, client, user):
        """Test a request with a missing password."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        user.set_password("password")
        payload = dict(curr_password="password", password_confirm="foobar")
        rv = client.post(
            "/v1/auth/password/update", json=payload, headers={"Authorization": token}
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to update your password."

    def test_endpoint_no_password_confirm(self, app, client, user):
        """Test a request with a missing password confirmation."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        user.set_password("password")
        payload = dict(curr_password="password", new_password="foobar")
        rv = client.post(
            "/v1/auth/password/update", json=payload, headers={"Authorization": token}
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to update your password."

    def test_endpoint_no_password_match(self, app, client, user):
        """Test a request with a different passwords."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        user.set_password("password")
        payload = dict(
            curr_password="password", new_password="foobar", password_confirm="foobaz"
        )
        rv = client.post(
            "/v1/auth/password/update", json=payload, headers={"Authorization": token}
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to update your password."

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.get(
            "/v1/auth/email/confirm/token", headers={"Authorization": token}
        )
        assert rv.status_code == 405

    def test_bad_request(self, app, client, user):
        """Test a request with no body."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post("/v1/auth/email/update", headers={"Authorization": token})
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid request."

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        user.set_password("password")
        payload = dict(
            curr_password="password", new_password="foobar", password_confirm="foobar"
        )
        rv = client.post("/v1/auth/password/update", json=payload)
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"


@pytest.mark.usefixtures("db")
class TestAuthPasswordReset:
    """Test the email confirmation request endpoint."""

    @mock.patch("aggrep.api.views.send_email")
    def test_endpoint(self, mock_email, app, client, user):
        """Test a successful request."""
        payload = dict(email=user.email)
        rv = client.post("/v1/auth/password/reset", json=payload)
        assert rv.status_code == 200
        json_data = rv.get_json()
        msg = "A password reset link has been sent to your email address."
        assert json_data["msg"] == msg
        assert mock_email.called_once

    def test_endpoint_invalid_email(self, app, client):
        """Test an unsuccessful request."""
        payload = dict(email="foo@bar.com")
        rv = client.post("/v1/auth/password/reset", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "The email address provided does not exist."

    def test_endpoint_no_data(self, app, client):
        """Test an unsuccessful request."""
        payload = dict()
        rv = client.post("/v1/auth/password/reset", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Request Unsuccessful"

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.get("/v1/auth/password/reset")
        assert rv.status_code == 405

    def test_bad_request(self, app, client, user):
        """Test a request with no body."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post("/v1/auth/password/reset", headers={"Authorization": token})
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid request."


@pytest.mark.usefixtures("db")
class TestAuthPasswordResetConfirm:
    """Test the email confirmation request endpoint."""

    @mock.patch("aggrep.api.views.send_email")
    def test_endpoint(self, mock_email, app, client, user):
        """Test a successful request."""
        with app.app_context():
            reset_token = user.get_reset_password_token()

        payload = dict(
            token=reset_token, new_password="foobar", password_confirm="foobar"
        )
        rv = client.post("/v1/auth/password/reset/confirm", json=payload)
        assert rv.status_code == 200
        json_data = rv.get_json()
        assert json_data["msg"] == "Your password has been updated."
        assert mock_email.called_once

    def test_endpoint_no_token(self, app, client, user):
        """Test a request with a missing token."""
        payload = dict(new_password="foobar", password_confirm="foobar")
        rv = client.post("/v1/auth/password/reset/confirm", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete password update."

    def test_endpoint_no_password(self, app, client, user):
        """Test a request with a missing password."""
        with app.app_context():
            reset_token = user.get_reset_password_token()

        payload = dict(token=reset_token, password_confirm="foobar")
        rv = client.post("/v1/auth/password/reset/confirm", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete password update."

    def test_endpoint_no_password_confirm(self, app, client, user):
        """Test a request with a missing password confirmation."""
        with app.app_context():
            reset_token = user.get_reset_password_token()

        payload = dict(token=reset_token, new_password="foobar")
        rv = client.post("/v1/auth/password/reset/confirm", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete password update."

    def test_endpoint_no_password_match(self, app, client, user):
        """Test a request with a different passwords."""
        with app.app_context():
            reset_token = user.get_reset_password_token()

        payload = dict(
            token=reset_token, new_password="foobar", password_confirm="foobaz"
        )
        rv = client.post("/v1/auth/password/reset/confirm", json=payload)
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete password update."

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.get("/v1/auth/email/confirm/token")
        assert rv.status_code == 405

    def test_bad_request(self, app, client, user):
        """Test a request with no body."""
        rv = client.post("/v1/auth/email/confirm/token")
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid request."
