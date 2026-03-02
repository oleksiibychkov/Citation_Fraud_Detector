"""Tests for notification dispatcher."""

from __future__ import annotations

from unittest.mock import patch

from cfd.config.settings import Settings
from cfd.notifications.dispatcher import dispatch_score_change


def _settings(**overrides) -> Settings:
    base = {
        "supabase_url": "",
        "supabase_key": "",
        "notification_score_threshold": 0.1,
        "notification_email_enabled": False,
        "notification_email_to": "",
        "notification_webhook_url": "",
    }
    base.update(overrides)
    return Settings(**base)


class TestDispatcher:
    def test_below_threshold_no_dispatch(self):
        """Delta below threshold → no channels notified."""
        s = _settings(notification_email_enabled=True, notification_email_to="x@test.com")
        result = dispatch_score_change(
            settings=s, author_name="Test", author_id=1,
            old_score=0.50, new_score=0.55,  # delta=0.05 < 0.1
        )
        assert result == []

    @patch("cfd.notifications.email.send_score_change_email", return_value=True)
    def test_email_dispatched(self, mock_email):
        s = _settings(
            notification_email_enabled=True,
            notification_email_to="admin@test.com",
            notification_smtp_host="smtp.test.com",
        )
        result = dispatch_score_change(
            settings=s, author_name="Author A", author_id=1,
            old_score=0.30, new_score=0.60,  # delta=0.30 ≥ 0.1
        )
        assert "email" in result
        mock_email.assert_called_once()

    @patch("cfd.notifications.webhook.send_score_change_webhook", return_value=True)
    def test_webhook_dispatched(self, mock_webhook):
        s = _settings(notification_webhook_url="https://hook.example.com/cfd")
        result = dispatch_score_change(
            settings=s, author_name="Author B", author_id=2,
            old_score=0.10, new_score=0.50,
        )
        assert "webhook" in result
        mock_webhook.assert_called_once()

    @patch("cfd.notifications.email.send_score_change_email", return_value=True)
    @patch("cfd.notifications.webhook.send_score_change_webhook", return_value=True)
    def test_both_channels(self, mock_webhook, mock_email):
        s = _settings(
            notification_email_enabled=True,
            notification_email_to="admin@test.com",
            notification_smtp_host="smtp.test.com",
            notification_webhook_url="https://hook.test.com",
        )
        result = dispatch_score_change(
            settings=s, author_name="Author C", author_id=3,
            old_score=0.10, new_score=0.80,
        )
        assert "email" in result
        assert "webhook" in result

    @patch("cfd.notifications.email.send_score_change_email", return_value=False)
    def test_email_failure_graceful(self, mock_email):
        s = _settings(
            notification_email_enabled=True,
            notification_email_to="admin@test.com",
            notification_smtp_host="smtp.test.com",
        )
        result = dispatch_score_change(
            settings=s, author_name="Author D", author_id=4,
            old_score=0.10, new_score=0.50,
        )
        assert "email" not in result

    @patch("cfd.notifications.webhook.send_score_change_webhook", return_value=False)
    def test_webhook_failure_graceful(self, mock_webhook):
        s = _settings(notification_webhook_url="https://hook.test.com")
        result = dispatch_score_change(
            settings=s, author_name="Author E", author_id=5,
            old_score=0.10, new_score=0.50,
        )
        assert "webhook" not in result

    def test_no_channels_configured(self):
        s = _settings()
        result = dispatch_score_change(
            settings=s, author_name="Author F", author_id=6,
            old_score=0.10, new_score=0.90,
        )
        assert result == []

    def test_negative_delta_still_dispatches(self):
        """Score decrease also triggers notification if |delta| >= threshold."""
        with patch("cfd.notifications.webhook.send_score_change_webhook", return_value=True):
            s = _settings(notification_webhook_url="https://hook.test.com")
            result = dispatch_score_change(
                settings=s, author_name="Author G", author_id=7,
                old_score=0.80, new_score=0.30,  # delta=-0.50, |delta|=0.50 ≥ 0.1
            )
            assert "webhook" in result
