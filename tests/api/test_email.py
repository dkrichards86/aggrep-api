"""Tests for the email module."""
from unittest import TestCase, mock

import pytest

from aggrep.api.email import send_email


@pytest.mark.usefixtures("app")
class TestEmail(TestCase):
    """Email tests."""

    @mock.patch("aggrep.mail.send_email")
    def test_send_email(self, mock_mail):
        """Test the send_email function."""

        send_email(
            dict(
                subject="Test Subject",
                recipients=["qux@quux.com"],
                text_body="test body",
                html_body="<b>test body</b>",
            )
        )

        assert mock_mail.call_count == 1
