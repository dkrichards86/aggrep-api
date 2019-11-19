"""Test forms."""
import pytest

from aggrep.api.forms import (
    ConfirmEmailForm,
    LoginForm,
    RegisterForm,
    RequestResetForm,
    ResetPasswordForm,
    UpdateEmailForm,
    UpdatePasswordForm,
)


@pytest.mark.usefixtures("db")
class TestLoginForm:
    """Login form."""

    def test_validate_success(self, user):
        """Submission successful."""
        form = LoginForm(email=user.email, password="example")
        assert form.validate() is True

    def test_email_required(self):
        """Test that email is a required field."""
        form = LoginForm(password="example")
        assert form.validate() is False
        assert "Email is required." in form.email.errors

    def test_email_is_valid(self):
        """Test that email is validated properly."""
        form = LoginForm(email="foobar", password="example")
        assert form.validate() is False
        assert "Email is invalid." in form.email.errors

    def test_password_required(self, user):
        """Test that email is a required field."""
        form = LoginForm(email=user.email)
        assert form.validate() is False
        assert "Password is required." in form.password.errors


@pytest.mark.usefixtures("db")
class TestRegisterForm:
    """Register form."""

    def test_email_required(self):
        """Test that email is a required field."""
        form = RegisterForm(password="example", password_confirm="example")
        assert form.validate() is False
        assert "Email is required." in form.email.errors

    def test_email_is_valid(self):
        """Test that email is validated properly."""
        form = RegisterForm(
            email="heyyo", password="example", password_confirm="example"
        )
        assert form.validate() is False
        assert "Email is invalid." in form.email.errors

    def test_password_required(self, user):
        """Test that password is a required field."""
        form = RegisterForm(email="new@test.test", password_confirm="example")
        assert form.validate() is False
        assert "Password is required." in form.password.errors

    def test_password_confirm_required(self, user):
        """Test that password_confirm is a required field."""
        form = RegisterForm(email="new@test.test", password="example")
        assert form.validate() is False
        assert "This field is required." in form.password_confirm.errors

    def test_passwords_match(self, user):
        """Test that passwords match."""
        form = RegisterForm(
            email="new@test.test", password="example", password_confirm="examplary"
        )
        assert form.validate() is False
        assert "Passwords must match." in form.password_confirm.errors

    def test_validate_email_already_registered(self, user):
        """Enter email that is already registered."""
        form = RegisterForm(
            email=user.email, password="example", password_confirm="example"
        )

        assert form.validate() is False
        assert "Email already registered" in form.email.errors

    def test_validate_success(self, db):
        """Register with success."""
        form = RegisterForm(
            email="new@test.test", password="example", password_confirm="example"
        )
        assert form.validate() is True


@pytest.mark.usefixtures("db")
class TestConfirmEmailForm:
    """Confirm email form."""

    def test_validate_success(self, user):
        """Submission successful."""
        form = ConfirmEmailForm(token="foobar")
        assert form.validate() is True

    def test_token_required(self):
        """Test that email is a required field."""
        form = ConfirmEmailForm()
        assert form.validate() is False
        assert "Token is required." in form.token.errors


@pytest.mark.usefixtures("db")
class TestRequestResetForm:
    """Request reset form."""

    def test_validate_success(self, user):
        """Submission successful."""
        form = RequestResetForm(email="foo@bar.com")
        assert form.validate() is True

    def test_email_required(self):
        """Test that email is a required field."""
        form = RequestResetForm(password="example")
        assert form.validate() is False
        assert "Email is required." in form.email.errors

    def test_email_is_valid(self):
        """Test that email is validated properly."""
        form = RequestResetForm(email="foobar", password="example")
        assert form.validate() is False
        assert "Email is invalid." in form.email.errors


@pytest.mark.usefixtures("db")
class TestResetPasswordForm:
    """Reset password form."""

    def test_validate_success(self):
        """Submission successful."""
        form = ResetPasswordForm(
            token="foobar", new_password="ok", password_confirm="ok"
        )
        assert form.validate() is True

    def test_token_required(self):
        """Test that email is a required field."""
        form = ResetPasswordForm(new_password="ok", password_confirm="ok")
        assert form.validate() is False
        assert "Token is required." in form.token.errors

    def test_password_required(self):
        """Test that password is a required field."""
        form = ResetPasswordForm(token="foobar", password_confirm="ok")
        assert form.validate() is False
        assert "Password is required." in form.new_password.errors

    def test_password_confirm_required(self):
        """Test that password_confirm is a required field."""
        form = ResetPasswordForm(token="foobar", new_password="ok")
        assert form.validate() is False
        assert "This field is required." in form.password_confirm.errors

    def test_passwords_match(self):
        """Test that passwords match."""
        form = ResetPasswordForm(
            token="foobar", new_password="ok", password_confirm="not ok"
        )
        assert form.validate() is False
        assert "Passwords must match." in form.password_confirm.errors


@pytest.mark.usefixtures("db")
class TestUpdatePasswordForm:
    """Reset password form."""

    def test_validate_success(self):
        """Submission successful."""
        form = UpdatePasswordForm(
            curr_password="foobar", new_password="ok", password_confirm="ok"
        )
        assert form.validate() is True

    def test_token_required(self):
        """Test that email is a required field."""
        form = UpdatePasswordForm(new_password="ok", password_confirm="ok")
        assert form.validate() is False
        assert "Current password is required." in form.curr_password.errors

    def test_password_required(self):
        """Test that password is a required field."""
        form = UpdatePasswordForm(curr_password="foobar", password_confirm="ok")
        assert form.validate() is False
        assert "New password is required." in form.new_password.errors

    def test_password_confirm_required(self):
        """Test that password_confirm is a required field."""
        form = UpdatePasswordForm(curr_password="foobar", new_password="ok")
        assert form.validate() is False
        assert "This field is required." in form.password_confirm.errors

    def test_passwords_match(self):
        """Test that passwords match."""
        form = UpdatePasswordForm(
            curr_password="foobar", new_password="ok", password_confirm="not ok"
        )
        assert form.validate() is False
        assert "Passwords must match." in form.password_confirm.errors


@pytest.mark.usefixtures("db")
class TestUpdateEmailForm:
    """Update email form."""

    def test_email_required(self):
        """Test that email is a required field."""
        form = UpdateEmailForm()
        assert form.validate() is False
        assert "Email is required." in form.email.errors

    def test_email_is_valid(self):
        """Test that email is validated properly."""
        form = UpdateEmailForm(email="heyyo")
        assert form.validate() is False
        assert "Email is invalid." in form.email.errors

    def test_validate_email_already_registered(self, user):
        """Enter email that is already registered."""
        form = UpdateEmailForm(email=user.email)

        assert form.validate() is False
        assert "Email already registered" in form.email.errors

    def test_validate_success(self, db):
        """Register with success."""
        form = UpdateEmailForm(email="new@test.test")
        assert form.validate() is True
