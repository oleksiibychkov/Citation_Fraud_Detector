"""Rate limiting via slowapi, keyed by API key."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address


def _key_func(request) -> str:
    """Extract rate limit key from X-API-Key header, fallback to IP."""
    return request.headers.get("x-api-key") or get_remote_address(request)


limiter = Limiter(key_func=_key_func)
