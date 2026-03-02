"""Clique detection results repository."""

from __future__ import annotations

from typing import Any


class CliqueRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "cliques"

    def save_many(self, cliques: list[dict], algorithm_version: str = "2.0.0") -> list[dict]:
        """Save detected cliques."""
        if not cliques:
            return []
        rows = [{**row, "algorithm_version": row.get("algorithm_version", algorithm_version)} for row in cliques]
        result = self._client.table(self._table).insert(rows).execute()
        return result.data or []

    def get_by_severity(self, severity: str | None = None, limit: int = 100) -> list[dict]:
        """Get cliques, optionally filtered by severity."""
        query = self._client.table(self._table).select("*")
        if severity:
            query = query.eq("severity", severity)
        query = query.order("detected_at", desc=True).limit(limit)
        result = query.execute()
        return result.data or []
