"""Model unit tests."""
from unittest import mock

import pytest
from flask_jwt_extended import create_access_token

from aggrep.models import Category, Feed, PostView, Source
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

        for i, instance in enumerate(SourceFactory.create_batch(25)):
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

        for i, instance in enumerate(CategoryFactory.create_batch(8)):
            instance.save()

        rv = client.get("/v1/categories")

        assert rv.status_code == 200
        json_data = rv.get_json()

        assert len(json_data["categories"]) == 8


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
        assert "errors" in json_data

    def test_missing_password(self, app, client, user):
        """Test a request with no password."""
        rv = client.post("/v1/auth/login", json=dict(email=user.email))
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete login."
        assert "errors" in json_data

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
