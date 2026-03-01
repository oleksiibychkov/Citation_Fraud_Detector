"""Citation repository for Supabase CRUD operations."""

from __future__ import annotations

from typing import Any

from cfd.data.models import Citation


class CitationRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "citations"

    def upsert_many(self, citations: list[Citation], target_author_id: int | None = None) -> list[dict]:
        """Upsert multiple citations."""
        if not citations:
            return []

        rows = []
        for cit in citations:
            rows.append({
                "source_work_id": cit.source_work_id,
                "target_work_id": cit.target_work_id,
                "source_author_id": cit.source_author_id,
                "target_author_id": cit.target_author_id or target_author_id,
                "citation_date": cit.citation_date.isoformat() if cit.citation_date else None,
                "is_self_citation": cit.is_self_citation,
                "source_api": cit.source_api,
            })

        # Batch upsert in chunks to avoid payload limits
        results = []
        chunk_size = 500
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            result = (
                self._client.table(self._table)
                .upsert(chunk, on_conflict="source_work_id,target_work_id")
                .execute()
            )
            results.extend(result.data or [])

        return results

    def get_by_target_author(self, author_id: int) -> list[dict]:
        """Get all citations where the given author is the target (incoming citations)."""
        result = self._client.table(self._table).select("*").eq("target_author_id", author_id).execute()
        return result.data or []

    def get_by_source_author(self, author_id: int) -> list[dict]:
        """Get all citations where the given author is the source (outgoing citations)."""
        result = self._client.table(self._table).select("*").eq("source_author_id", author_id).execute()
        return result.data or []
