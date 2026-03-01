"""Indicator repository for Supabase CRUD operations."""

from __future__ import annotations

from typing import Any


class IndicatorRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "indicators"

    def save_many(self, author_id: int, indicators: list[dict], algorithm_version: str = "1.0.0") -> list[dict]:
        """Save computed indicators for an author."""
        if not indicators:
            return []

        rows = []
        for ind in indicators:
            rows.append({
                "author_id": author_id,
                "indicator_type": ind["indicator_type"],
                "value": ind["value"],
                "details": ind.get("details"),
                "algorithm_version": algorithm_version,
            })

        result = self._client.table(self._table).insert(rows).execute()
        return result.data or []

    def get_by_author_id(self, author_id: int) -> list[dict]:
        """Get latest indicators for an author."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("author_id", author_id)
            .order("calculated_at", desc=True)
            .execute()
        )
        return result.data or []
