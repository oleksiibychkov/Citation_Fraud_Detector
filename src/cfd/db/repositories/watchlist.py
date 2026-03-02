"""Watchlist repository for monitoring authors."""

from __future__ import annotations

from typing import Any


class WatchlistRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "watchlist"

    def add(self, author_id: int, reason: str | None = None, notes: str | None = None) -> dict:
        """Add an author to the watchlist."""
        row = {"author_id": author_id, "reason": reason, "notes": notes, "is_active": True}
        result = (
            self._client.table(self._table)
            .upsert(row, on_conflict="author_id")
            .execute()
        )
        data = result.data or []
        return data[0] if data else {}

    def remove(self, author_id: int) -> None:
        """Deactivate an author from the watchlist."""
        self._client.table(self._table).update({"is_active": False}).eq("author_id", author_id).execute()

    def get_active(self, limit: int = 100) -> list[dict]:
        """Get all active watchlist entries."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def set_sensitivity_overrides(self, author_id: int, overrides: dict) -> dict:
        """Set per-author sensitivity overrides (§4.4)."""
        result = (
            self._client.table(self._table)
            .update({"sensitivity_overrides": overrides})
            .eq("author_id", author_id)
            .execute()
        )
        data = result.data or []
        return data[0] if data else {}

    def get_with_author_info(self, limit: int = 100) -> list[dict]:
        """Get active watchlist entries joined with author info."""
        result = (
            self._client.table(self._table)
            .select("*, authors(id, surname, full_name, scopus_id, orcid)")
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
