"""Theorem hierarchy results repository."""

from __future__ import annotations

from typing import Any


class TheoremResultRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "theorem_results"

    def save_many(self, author_id: int, results: list[dict], algorithm_version: str = "2.0.0") -> list[dict]:
        """Save theorem hierarchy results for an author."""
        if not results:
            return []
        rows = []
        for r in results:
            rows.append({
                "author_id": author_id,
                "theorem_number": r["theorem_number"],
                "passed": r["passed"],
                "details": r.get("details"),
                "algorithm_version": algorithm_version,
            })
        result = self._client.table(self._table).insert(rows).execute()
        return result.data or []

    def get_by_author_id(self, author_id: int) -> list[dict]:
        """Get theorem results for an author."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("author_id", author_id)
            .order("calculated_at", desc=True)
            .execute()
        )
        return result.data or []
