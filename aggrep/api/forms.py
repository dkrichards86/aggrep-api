"""API forms."""
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email, EqualTo

from aggrep.models import User


class LoginForm(FlaskForm):
    """Login form."""

    email = EmailField(
        "email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Email is invalid."),
        ],
    )
    password = PasswordField(
        "password", validators=[DataRequired(message="Password is required.")]
    )


class RegisterForm(FlaskForm):
    """Registration form."""

    email = EmailField(
        "email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Email is invalid."),
        ],
    )
    password = PasswordField(
        "password", validators=[DataRequired(message="Password is required.")]
    )
    password_confirm = PasswordField(
        "password_confirm",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(RegisterForm, self).__init__(*args, **kwargs)

    def validate(self):
        """Validate the form."""
        initial_validation = super(RegisterForm, self).validate()
        if not initial_validation:
            return False
        user = User.query.filter_by(email=self.email.data).first()
        if user:
            self.email.errors.append("Email already registered")
            return False
        return True


class ConfirmEmailForm(FlaskForm):
    """Confirm email form."""

    token = StringField(
        "token", validators=[DataRequired(message="Token is required.")]
    )


class RequestResetForm(FlaskForm):
    """Request a password reset form."""

    email = EmailField(
        "email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Email is invalid."),
        ],
    )


class ResetPasswordForm(FlaskForm):
    """Reset password form."""

    token = StringField(
        "token", validators=[DataRequired(message="Token is required.")]
    )
    new_password = PasswordField(
        "new_password", validators=[DataRequired(message="Password is required.")]
    )
    password_confirm = PasswordField(
        "password_confirm",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match."),
        ],
    )


class UpdatePasswordForm(FlaskForm):
    """Update password form."""

    curr_password = PasswordField(
        "curr_password",
        validators=[DataRequired(message="Current password is required.")],
    )
    new_password = PasswordField(
        "new_password", validators=[DataRequired(message="New password is required.")]
    )
    password_confirm = PasswordField(
        "password_confirm",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match."),
        ],
    )


class UpdateEmailForm(FlaskForm):
    """Update email form."""

    email = EmailField(
        "email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Email is invalid."),
        ],
    )

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(UpdateEmailForm, self).__init__(*args, **kwargs)

    def validate(self):
        """Validate the form."""
        initial_validation = super(UpdateEmailForm, self).validate()
        if not initial_validation:
            return False
        user = User.query.filter_by(email=self.email.data).first()
        if user:
            self.email.errors.append("Email already registered")
            return False
        return True
