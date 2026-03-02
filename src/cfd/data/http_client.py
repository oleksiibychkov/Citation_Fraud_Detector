"""HTTP client with caching, rate limiting, and retry logic."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from cfd.exceptions import APIError, RateLimitError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket-style rate limiter."""

    def __init__(self, requests_per_second: int):
        self._interval = 1.0 / max(requests_per_second, 1)
        self._last_request_time = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)
        self._last_request_time = time.monotonic()


class CachedHttpClient:
    """HTTP client with Supabase-backed cache, rate limiting, and retry."""

    def __init__(
        self,
        supabase_client: Any | None = None,
        rate_limiter: RateLimiter | None = None,
        cache_ttl_days: int = 7,
        max_retries: int = 3,
    ):
        self._http = httpx.Client(timeout=30.0, follow_redirects=True)
        self._supabase = supabase_client
        self._rate_limiter = rate_limiter or RateLimiter(10)
        self._cache_ttl_days = cache_ttl_days
        self._max_retries = max_retries

    def close(self) -> None:
        self._http.close()

    def _cache_key(self, url: str, params: dict | None) -> str:
        raw = json.dumps({"url": url, "params": params or {}}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> dict | None:
        if self._supabase is None:
            return None
        try:
            result = (
                self._supabase.table("api_cache")
                .select("response_data, expires_at")
                .eq("cache_key", key)
                .execute()
            )
            if result.data:
                row = result.data[0]
                expires = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
                if expires > datetime.now(UTC):
                    return row["response_data"]
        except Exception:
            logger.debug("Cache lookup failed, proceeding without cache", exc_info=True)
        return None

    def _set_cached(self, key: str, url: str, params: dict | None, data: dict, source_api: str) -> None:
        if self._supabase is None:
            return
        try:
            expires = datetime.now(UTC) + timedelta(days=self._cache_ttl_days)
            self._supabase.table("api_cache").upsert(
                {
                    "cache_key": key,
                    "endpoint": url[:500],
                    "params": params or {},
                    "response_data": data,
                    "source_api": source_api,
                    "expires_at": expires.isoformat(),
                },
                on_conflict="cache_key",
            ).execute()
        except Exception:
            logger.debug("Cache write failed", exc_info=True)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, RateLimitError, APIError)),
        reraise=True,
    )
    def _do_request(self, url: str, params: dict | None, headers: dict | None) -> httpx.Response:
        self._rate_limiter.wait()
        response = self._http.get(url, params=params, headers=headers)
        if response.status_code == 429:
            retry_after_raw = response.headers.get("Retry-After", "5")
            try:
                retry_after = int(retry_after_raw)
            except ValueError:
                retry_after = 5
            logger.warning("Rate limited. Waiting %d seconds.", retry_after)
            time.sleep(retry_after)
            raise RateLimitError("Rate limit exceeded")
        if response.status_code >= 500:
            raise APIError(f"Server error {response.status_code}: {url}")
        response.raise_for_status()
        return response

    def get(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        source_api: str = "openalex",
        use_cache: bool = True,
    ) -> dict:
        """Make a GET request with optional caching."""
        key = self._cache_key(url, params)

        if use_cache:
            cached = self._get_cached(key)
            if cached is not None:
                logger.debug("Cache hit: %s", url)
                return cached

        try:
            response = self._do_request(url, params, headers)
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(f"HTTP {e.response.status_code}: {url}") from e
        except httpx.ConnectError as e:
            raise APIError(f"Connection failed: {url}") from e

        if use_cache:
            self._set_cached(key, url, params, data, source_api)

        return data
