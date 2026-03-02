"""Audit log endpoint (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from cfd.api.auth import APIKeyInfo, require_role
from cfd.api.dependencies import get_repos
from cfd.api.schemas import AuditEntry

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=list[AuditEntry])
def get_audit_log(
    limit: int = Query(100, le=500, ge=1),
    offset: int = Query(0, ge=0),
    key_info: APIKeyInfo = Depends(require_role("admin")),
    repos: dict = Depends(get_repos),
):
    """Retrieve audit log entries. Admin only."""
    entries = repos["audit"].get_all(limit=limit, offset=offset)
    return [
        AuditEntry(
            id=e.get("id"),
            timestamp=str(e.get("timestamp", "")),
            action=e.get("action", ""),
            target_author_id=e.get("target_author_id"),
            details=e.get("details"),
            user_id=e.get("user_id"),
        )
        for e in entries
    ]
