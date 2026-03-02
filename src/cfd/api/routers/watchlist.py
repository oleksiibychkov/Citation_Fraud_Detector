"""Watchlist management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from cfd.api.auth import APIKeyInfo, require_role
from cfd.api.dependencies import get_repos
from cfd.api.schemas import SensitivityOverridesRequest, WatchlistAddRequest, WatchlistEntry, WatchlistHistoryEntry
from cfd.exceptions import AuthorNotFoundError

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.post("/add", response_model=WatchlistEntry)
def add_to_watchlist(
    body: WatchlistAddRequest,
    key_info: APIKeyInfo = Depends(require_role("analyst", "admin")),
    repos: dict = Depends(get_repos),
):
    """Add an author to the watchlist."""
    author = repos["author"].get_by_id(body.author_id)
    if not author:
        raise AuthorNotFoundError(f"Author {body.author_id} not found")

    result = repos["watchlist"].add(body.author_id, reason=body.reason, notes=body.notes)
    repos["audit"].log(
        "add_watchlist", target_author_id=body.author_id,
        details={"reason": body.reason, "api_key": key_info.name},
        user_id=key_info.name, api_key_id=key_info.key_id,
    )

    return WatchlistEntry(
        author_id=result.get("author_id", body.author_id),
        reason=result.get("reason"),
        notes=result.get("notes"),
        is_active=result.get("is_active", True),
        created_at=str(result.get("created_at", "")),
    )


@router.get("", response_model=list[WatchlistEntry])
def list_watchlist(
    key_info: APIKeyInfo = Depends(require_role("reader", "analyst", "admin")),
    repos: dict = Depends(get_repos),
):
    """List all active watchlist entries."""
    entries = repos["watchlist"].get_active()
    return [
        WatchlistEntry(
            author_id=e.get("author_id"),
            reason=e.get("reason"),
            notes=e.get("notes"),
            is_active=e.get("is_active", True),
            created_at=str(e.get("created_at", "")),
        )
        for e in entries
    ]


@router.get("/{author_id}/history", response_model=list[WatchlistHistoryEntry])
def get_watchlist_history(
    author_id: int,
    key_info: APIKeyInfo = Depends(require_role("reader", "analyst", "admin")),
    repos: dict = Depends(get_repos),
):
    """Get historical snapshots for a watchlisted author."""
    snapshots = repos["snapshot"].get_by_author_id(author_id)
    return [
        WatchlistHistoryEntry(
            snapshot_date=str(s.get("snapshot_date", "")),
            fraud_score=s.get("fraud_score"),
            confidence_level=s.get("confidence_level"),
            indicator_values=s.get("indicator_values"),
            algorithm_version=s.get("algorithm_version"),
        )
        for s in snapshots
    ]


@router.put("/{author_id}/sensitivity")
def set_sensitivity_overrides(
    author_id: int,
    body: SensitivityOverridesRequest,
    key_info: APIKeyInfo = Depends(require_role("analyst", "admin")),
    repos: dict = Depends(get_repos),
):
    """Set per-author sensitivity overrides (§4.4)."""
    result = repos["watchlist"].set_sensitivity_overrides(author_id, body.overrides)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No watchlist entry for author {author_id}")
    repos["audit"].log(
        "set_sensitivity", target_author_id=author_id,
        details={"overrides": body.overrides, "api_key": key_info.name},
        user_id=key_info.name, api_key_id=key_info.key_id,
    )
    return {"status": "ok", "author_id": author_id, "overrides": body.overrides}
