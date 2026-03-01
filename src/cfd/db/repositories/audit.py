"""Audit log repository (append-only)."""

from __future__ import annotations

from typing import Any


class AuditLogRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "audit_log"

    def log(self, action: str, target_author_id: int | None = None, details: dict | None = None) -> dict:
        """Append an audit log entry."""
        row = {"action": action, "target_author_id": target_author_id, "details": details}
        result = self._client.table(self._table).insert(row).execute()
        data = result.data or []
        return data[0] if data else {}

    def get_by_author(self, author_id: int, limit: int = 100) -> list[dict]:
        """Get audit entries for a specific author."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("target_author_id", author_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
