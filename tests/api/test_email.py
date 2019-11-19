"""Tests for the email module."""
from unittest import TestCase

import pytest

from aggrep import mail
from aggrep.api.email import send_email


@pytest.mark.usefixtures("app")
class TestEmail(TestCase):
    """Email tests."""

    def test_send_email(self):
        """Test the send_email function."""
        with mail.record_messages() as outbox:
            send_email(
                dict(
                    subject="Test Subject",
                    recipients=["qux@quux.com"],
                    text_body="test body",
                    html_body="<b>test body</b>",
                )
            )
        assert len(outbox) == 1
        assert outbox[0].subject == "Test Subject"
