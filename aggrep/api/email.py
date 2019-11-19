"""Ticker email module."""
from flask import current_app
from flask_mail import Message

from aggrep import celery, mail


@celery.task
def send_email(data):
    """Send an email asynchronously."""
    msg = Message(
        data["subject"],
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=data["recipients"],
    )
    msg.body = data["text_body"]
    msg.html = data["html_body"]
    with current_app.app_context():
        mail.send(msg)
