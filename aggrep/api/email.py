"""Aggregate Report email module."""
from flask import current_app
from sendgrid.helpers.mail import Email

from aggrep import mail


def send_email(data):
    """Send an email asynchronously."""

    message = dict(
        subject=data["subject"],
        from_email=current_app.config["SENDGRID_DEFAULT_FROM"],
        to_email=[Email(addr) for addr in data["recipients"]],
        text=data["text_body"],
        html=data["html_body"],
    )

    with current_app.app_context():
        mail.send_email(**message)
