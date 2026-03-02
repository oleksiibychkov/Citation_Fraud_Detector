"""Report evidence repository."""

from __future__ import annotations

from typing import Any


class ReportEvidenceRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "report_evidence"

    def save_many(self, author_id: int, evidence_list: list[dict], algorithm_version: str) -> list[dict]:
        """Save multiple evidence records for an author."""
        rows = [
            {
                "author_id": author_id,
                "evidence_type": e.get("evidence_type", "indicator"),
                "indicator_type": e.get("indicator_type"),
                "data": e.get("data"),
                "description": e.get("description"),
                "algorithm_version": algorithm_version,
            }
            for e in evidence_list
        ]
        if not rows:
            return []
        result = self._client.table(self._table).insert(rows).execute()
        return result.data or []

    def get_by_author(self, author_id: int, limit: int = 100) -> list[dict]:
        """Get evidence records for an author."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("author_id", author_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
