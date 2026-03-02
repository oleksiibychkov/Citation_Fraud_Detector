"""Webhook notification sender (§4.4/§11)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_BLOCKED_HOSTS = frozenset({
    "localhost", "127.0.0.1", "::1", "0.0.0.0",
    "metadata.google.internal", "169.254.169.254",
})


def _validate_webhook_url(url: str) -> None:
    """Validate webhook URL to prevent SSRF attacks."""
    import ipaddress

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Webhook URL must use http(s), got {parsed.scheme!r}")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("Webhook URL has no hostname")
    if hostname in _BLOCKED_HOSTS:
        raise ValueError(f"Webhook URL hostname {hostname!r} is blocked")
    # Block private/loopback IPs (including IPv4-mapped IPv6 like ::ffff:127.0.0.1)
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"Webhook URL points to non-public IP: {hostname}")
    except ValueError as e:
        if "non-public" in str(e):
            raise
        # Not an IP address — check hostname patterns
        if hostname.startswith("10.") or hostname.startswith("192.168."):
            raise ValueError(f"Webhook URL points to private IP: {hostname}") from None
        if hostname.startswith("172."):
            parts = hostname.split(".")
            if len(parts) >= 2 and parts[1].isdigit():
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    raise ValueError(f"Webhook URL points to private IP: {hostname}") from None


def send_score_change_webhook(
    *,
    url: str,
    author_name: str,
    author_id: int | None,
    old_score: float,
    new_score: float,
    secret: str = "",
    timeout: float = 10.0,
) -> bool:
    """POST a score-change payload to a webhook URL.

    Returns True on success (2xx), False on failure (non-blocking).
    """
    try:
        _validate_webhook_url(url)
    except ValueError:
        logger.warning("Blocked webhook to %s: SSRF protection", url)
        return False

    payload = {
        "event": "score_change",
        "timestamp": datetime.now(UTC).isoformat(),
        "author_name": author_name,
        "author_id": author_id,
        "old_score": round(old_score, 4),
        "new_score": round(new_score, 4),
        "delta": round(new_score - old_score, 4),
    }

    headers = {"Content-Type": "application/json"}
    body_bytes = json.dumps(payload, sort_keys=True).encode()

    if secret:
        signature = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
        headers["X-CFD-Signature"] = signature

    try:
        resp = httpx.post(url, content=body_bytes, headers=headers, timeout=timeout)
        if resp.is_success:
            logger.info("Webhook sent to %s for %s (status=%d)", url, author_name, resp.status_code)
            return True
        logger.warning("Webhook to %s returned %d", url, resp.status_code)
        return False
    except Exception:
        logger.warning("Failed to send webhook to %s", url, exc_info=True)
        return False
