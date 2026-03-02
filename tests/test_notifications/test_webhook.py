"""Tests for webhook notification sender (§4.4/§11)."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from cfd.notifications.webhook import send_score_change_webhook


class TestSendScoreChangeWebhook:
    """Tests for send_score_change_webhook function."""

    @patch("cfd.notifications.webhook.httpx.post")
    def test_successful_post_without_secret(self, mock_post):
        """Webhook POST succeeds with 200 and no HMAC signature."""
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = send_score_change_webhook(
            url="https://hook.example.com/cfd",
            author_name="Ivanenko",
            author_id=42,
            old_score=0.20,
            new_score=0.65,
        )

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs["headers"] if "headers" in call_kwargs.kwargs else call_kwargs[1]["headers"]
        assert "X-CFD-Signature" not in headers
        # Verify payload content
        body_bytes = call_kwargs.kwargs.get("content") or call_kwargs[1].get("content")
        payload = json.loads(body_bytes)
        assert payload["event"] == "score_change"
        assert payload["author_name"] == "Ivanenko"
        assert payload["author_id"] == 42
        assert payload["old_score"] == 0.20
        assert payload["new_score"] == 0.65
        assert payload["delta"] == 0.45

    @patch("cfd.notifications.webhook.httpx.post")
    def test_successful_post_with_hmac_secret(self, mock_post):
        """Webhook POST includes X-CFD-Signature when a secret is provided."""
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = send_score_change_webhook(
            url="https://hook.example.com/cfd",
            author_name="Petrenko",
            author_id=99,
            old_score=0.10,
            new_score=0.50,
            secret="my-webhook-secret",
        )

        assert result is True
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        body_bytes = call_kwargs.kwargs.get("content") or call_kwargs[1].get("content")
        assert "X-CFD-Signature" in headers
        # Verify HMAC matches
        expected_sig = hmac.new(
            b"my-webhook-secret", body_bytes, hashlib.sha256
        ).hexdigest()
        assert headers["X-CFD-Signature"] == expected_sig

    @patch("cfd.notifications.webhook.httpx.post")
    def test_non_success_status_returns_false(self, mock_post):
        """Webhook returns False when server responds with non-2xx status."""
        mock_resp = MagicMock()
        mock_resp.is_success = False
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        result = send_score_change_webhook(
            url="https://hook.example.com/cfd",
            author_name="Kovalenko",
            author_id=7,
            old_score=0.30,
            new_score=0.70,
        )

        assert result is False

    @patch("cfd.notifications.webhook.httpx.post")
    def test_connection_error_returns_false(self, mock_post):
        """Webhook returns False when the HTTP request raises an exception."""
        mock_post.side_effect = Exception("Connection timed out")

        result = send_score_change_webhook(
            url="https://unreachable.example.com",
            author_name="Bondarenko",
            author_id=None,
            old_score=0.50,
            new_score=0.90,
            timeout=5.0,
        )

        assert result is False
        mock_post.assert_called_once()
