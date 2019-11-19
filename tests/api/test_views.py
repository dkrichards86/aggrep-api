"""Model unit tests."""
from flask_jwt_extended import create_access_token


class TestAuthTokenConfirm:
    """Test the auth token confirmation endpoint."""

    def test_endpoint(self, app, client, user):
        """Test a successful request."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.get("/api/v1/auth/token/confirm", headers={"Authorization": token})
        assert rv.status_code == 200
        json_data = rv.get_json()
        assert json_data["msg"] == "Token verification successful!"
        assert "access_token" in json_data
        assert "user" in json_data

    def test_no_auth(self, app, client, user):
        """Test a request with no auth token."""
        rv = client.get("/api/v1/auth/token/confirm")
        assert rv.status_code == 401
        json_data = rv.get_json()
        assert json_data["msg"] == "Missing Authorization Header"

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.post("/api/v1/auth/token/confirm")
        assert rv.status_code == 405


class TestAuthLogin:
    """Test the login endpoint."""

    def test_endpoint(self, app, client, user):
        """Test a successful request."""
        rv = client.post(
            "/api/v1/auth/login", json=dict(email=user.email, password="foobar")
        )
        assert rv.status_code == 200
        json_data = rv.get_json()
        assert json_data["msg"] == "Login Successful"
        assert "access_token" in json_data
        assert "user" in json_data

    def test_incorrect_email(self, app, client, user):
        """Test a request with an incorrect email."""
        rv = client.post(
            "/api/v1/auth/login", json=dict(email="foo@bar.com", password="foobar")
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid email address or password"

    def test_incorrect_password(self, app, client, user):
        """Test a request with an incorrect password."""
        rv = client.post(
            "/api/v1/auth/login", json=dict(email="foo@bar.com", password="foobaz")
        )
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid email address or password"

    def test_missing_email(self, app, client, user):
        """Test a request with no email."""
        rv = client.post("/api/v1/auth/login", json=dict(password="foobar"))
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete login."
        assert "errors" in json_data

    def test_missing_password(self, app, client, user):
        """Test a request with no password."""
        rv = client.post("/api/v1/auth/login", json=dict(email=user.email))
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Unable to complete login."
        assert "errors" in json_data

    def test_invalid_method(self, app, client, user):
        """Test a request with an invalid HTTP method."""
        rv = client.get("/api/v1/auth/login")
        assert rv.status_code == 405

    def test_already_logged_in(self, app, client, user):
        """Test a request with a logged in user."""
        with app.app_context():
            token = "Bearer {}".format(create_access_token(user.email))

        rv = client.post("/api/v1/auth/login", headers={"Authorization": token})
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "You are already logged in."

    def test_bad_request(self, app, client, user):
        """Test a request with no body."""
        rv = client.post("/api/v1/auth/login")
        assert rv.status_code == 400
        json_data = rv.get_json()
        assert json_data["msg"] == "Invalid request."
