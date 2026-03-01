"""Snapshots repository for tracking author metrics over time."""

from __future__ import annotations

from typing import Any


class SnapshotRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "snapshots"

    def save(self, snapshot: dict) -> dict:
        """Save a new snapshot."""
        result = self._client.table(self._table).insert(snapshot).execute()
        data = result.data or []
        return data[0] if data else {}

    def get_by_author_id(self, author_id: int, limit: int = 50) -> list[dict]:
        """Get snapshots for an author, ordered by date descending."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("author_id", author_id)
            .order("snapshot_date", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
