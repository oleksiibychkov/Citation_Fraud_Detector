"""Tests for email notification sender (§4.4/§11)."""

from __future__ import annotations

import email
from unittest.mock import MagicMock, patch

from cfd.notifications.email import send_score_change_email


class TestSendScoreChangeEmail:
    """Tests for send_score_change_email function."""

    @patch("cfd.notifications.email.smtplib.SMTP")
    def test_send_without_auth(self, mock_smtp_cls):
        """Email is sent successfully without SMTP authentication."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_score_change_email(
            to_address="admin@example.com",
            author_name="Ivanenko",
            old_score=0.20,
            new_score=0.65,
            smtp_host="smtp.test.local",
            smtp_port=25,
        )

        assert result is True
        mock_smtp_cls.assert_called_once_with("smtp.test.local", 25, timeout=10)
        mock_server.sendmail.assert_called_once()
        # Verify sendmail args: from, to_list, message string
        call_args = mock_server.sendmail.call_args
        assert call_args[0][0] == "cfd-alerts@localhost"
        assert call_args[0][1] == ["admin@example.com"]
        assert "Ivanenko" in call_args[0][2]
        # starttls is always called for non-SSL ports (security fix)
        mock_server.starttls.assert_called_once()
        # login should NOT be called when no credentials
        mock_server.login.assert_not_called()

    @patch("cfd.notifications.email.smtplib.SMTP")
    def test_send_with_auth(self, mock_smtp_cls):
        """Email is sent successfully with SMTP TLS authentication."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_score_change_email(
            to_address="admin@example.com",
            author_name="Petrenko",
            old_score=0.10,
            new_score=0.80,
            smtp_host="smtp.test.local",
            smtp_port=587,
            smtp_user="user@test.local",
            smtp_password="secret123",
            from_address="alerts@cfd.org",
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.local", "secret123")
        call_args = mock_server.sendmail.call_args
        assert call_args[0][0] == "alerts@cfd.org"
        assert "Petrenko" in call_args[0][2]

    @patch("cfd.notifications.email.smtplib.SMTP")
    def test_send_failure_returns_false(self, mock_smtp_cls):
        """SMTP connection failure returns False instead of raising."""
        mock_smtp_cls.side_effect = ConnectionRefusedError("Connection refused")

        result = send_score_change_email(
            to_address="admin@example.com",
            author_name="Kovalenko",
            old_score=0.30,
            new_score=0.70,
            smtp_host="unreachable.host",
        )

        assert result is False

    @patch("cfd.notifications.email.smtplib.SMTP")
    def test_email_body_contains_score_details(self, mock_smtp_cls):
        """Email body includes author name, old/new scores, and delta."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_score_change_email(
            to_address="admin@example.com",
            author_name="Shevchenko",
            old_score=0.25,
            new_score=0.75,
            smtp_host="smtp.test.local",
        )

        sent_raw = mock_server.sendmail.call_args[0][2]
        # Parse the MIME message to get decoded body text
        parsed = email.message_from_string(sent_raw)
        body = parsed.get_payload(decode=True).decode("utf-8")
        assert "Shevchenko" in body
        assert "0.2500" in body  # old score
        assert "0.7500" in body  # new score
        assert "+0.5000" in body  # delta
