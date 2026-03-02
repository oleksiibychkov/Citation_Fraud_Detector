"""Audit log repository (append-only)."""

from __future__ import annotations

from typing import Any


class AuditLogRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "audit_log"

    def log(
        self,
        action: str,
        target_author_id: int | None = None,
        details: dict | None = None,
        user_id: str | None = None,
        api_key_id: int | None = None,
    ) -> dict:
        """Append an audit log entry."""
        row: dict[str, Any] = {"action": action, "target_author_id": target_author_id, "details": details}
        if user_id is not None:
            row["user_id"] = user_id
        if api_key_id is not None:
            row["api_key_id"] = api_key_id
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

    def get_all(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """Get all audit entries with pagination (admin use)."""
        result = (
            self._client.table(self._table)
            .select("*")
            .order("timestamp", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or []
