"""API cache operations using Supabase api_cache table."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class ApiCache:
    """Cache layer for API responses stored in Supabase."""

    def __init__(self, supabase_client: Any, ttl_days: int = 7):
        self._client = supabase_client
        self._ttl_days = ttl_days

    @staticmethod
    def make_key(endpoint: str, params: dict | None = None) -> str:
        raw = json.dumps({"url": endpoint, "params": params or {}}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, cache_key: str) -> dict | None:
        """Get cached response if not expired."""
        try:
            result = (
                self._client.table("api_cache")
                .select("response_data, expires_at")
                .eq("cache_key", cache_key)
                .execute()
            )
            if result.data:
                row = result.data[0]
                expires = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
                if expires > datetime.now(UTC):
                    return row["response_data"]
        except Exception:
            logger.debug("Cache get failed", exc_info=True)
        return None

    def set(self, cache_key: str, endpoint: str, params: dict | None, data: dict, source_api: str) -> None:
        """Store response in cache."""
        try:
            expires = datetime.now(UTC) + timedelta(days=self._ttl_days)
            self._client.table("api_cache").upsert({
                "cache_key": cache_key,
                "endpoint": endpoint[:500],
                "params": params or {},
                "response_data": data,
                "source_api": source_api,
                "expires_at": expires.isoformat(),
            }).execute()
        except Exception:
            logger.debug("Cache set failed", exc_info=True)

    def invalidate(self, cache_key: str) -> None:
        """Remove a specific cache entry."""
        try:
            self._client.table("api_cache").delete().eq("cache_key", cache_key).execute()
        except Exception:
            logger.debug("Cache invalidate failed", exc_info=True)

    def cleanup_expired(self) -> int:
        """Remove all expired cache entries. Returns count of removed entries."""
        try:
            now = datetime.now(UTC).isoformat()
            result = self._client.table("api_cache").delete().lt("expires_at", now).execute()
            return len(result.data) if result.data else 0
        except Exception:
            logger.debug("Cache cleanup failed", exc_info=True)
            return 0
