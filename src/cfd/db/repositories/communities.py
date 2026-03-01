"""Community detection results repository."""

from __future__ import annotations

from typing import Any


class CommunityRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "communities"

    def save_many(self, communities: list[dict], algorithm_version: str = "2.0.0") -> list[dict]:
        """Save community detection results."""
        if not communities:
            return []
        for row in communities:
            row.setdefault("algorithm_version", algorithm_version)
        result = self._client.table(self._table).insert(communities).execute()
        return result.data or []

    def get_by_author_id(self, author_id: int) -> list[dict]:
        """Get communities an author belongs to."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("author_id", author_id)
            .order("detected_at", desc=True)
            .execute()
        )
        return result.data or []
