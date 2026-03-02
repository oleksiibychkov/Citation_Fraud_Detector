"""Rate limiting via slowapi, keyed by hashed API key."""

from __future__ import annotations

import hashlib

from slowapi import Limiter
from slowapi.util import get_remote_address


def _key_func(request) -> str:
    """Extract rate limit key from X-API-Key header (hashed), fallback to IP."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    return get_remote_address(request)


limiter = Limiter(key_func=_key_func)
