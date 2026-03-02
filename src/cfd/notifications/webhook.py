"""Webhook notification sender (§4.4/§11)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)


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
