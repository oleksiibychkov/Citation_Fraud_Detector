"""API key authentication and role-based access control."""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, Request, status

logger = logging.getLogger(__name__)


@dataclass
class APIKeyInfo:
    """Validated API key metadata."""

    key_id: int | None
    name: str
    role: str  # "reader", "analyst", "admin"
    rate_limit_per_minute: int = 60


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_api_key(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-Key"),
) -> APIKeyInfo:
    """Validate API key from X-API-Key header.

    Checks the DB first (api_keys table), then falls back to
    the CFD_API_KEYS environment variable (comma-separated keys).
    """
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key header")

    # Try DB lookup
    supabase = getattr(request.app.state, "supabase", None)
    if supabase is not None:
        try:
            key_hash = _hash_key(x_api_key)
            result = (
                supabase.table("api_keys")
                .select("*")
                .eq("key_hash", key_hash)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            if result.data:
                row = result.data[0]
                # Update last_used_at
                with contextlib.suppress(Exception):
                    supabase.table("api_keys").update(
                        {"last_used_at": datetime.now(UTC).isoformat()}
                    ).eq("id", row["id"]).execute()
                return APIKeyInfo(
                    key_id=row["id"],
                    name=row.get("name", ""),
                    role=row.get("role", "reader"),
                    rate_limit_per_minute=row.get("rate_limit_per_minute", 60),
                )
        except Exception:
            logger.warning("DB API key lookup failed, trying env fallback", exc_info=True)

    # Env fallback: CFD_API_KEYS=key1,key2,key3 (all get admin role)
    from cfd.config.settings import Settings

    settings: Settings = getattr(request.app.state, "settings", None) or Settings()
    if settings.api_keys:
        env_keys = [k.strip() for k in settings.api_keys.split(",") if k.strip()]
        matched = False
        for k in env_keys:
            if hmac.compare_digest(x_api_key, k):
                matched = True
        if matched:
            return APIKeyInfo(key_id=None, name="env_key", role="admin", rate_limit_per_minute=120)

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def require_role(*allowed_roles: str):
    """Dependency factory: ensure the API key has one of the allowed roles."""

    async def _check(key_info: APIKeyInfo = Depends(get_api_key)) -> APIKeyInfo:
        if key_info.role not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return key_info

    return _check
