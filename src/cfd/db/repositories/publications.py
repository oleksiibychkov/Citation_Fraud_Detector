"""Publication repository for Supabase CRUD operations."""

from __future__ import annotations

from typing import Any

from cfd.data.models import Publication


class PublicationRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "publications"

    def upsert_many(self, author_id: int, publications: list[Publication]) -> list[dict]:
        """Upsert multiple publications for an author."""
        if not publications:
            return []

        rows = []
        for pub in publications:
            rows.append({
                "author_id": author_id,
                "work_id": pub.work_id,
                "doi": pub.doi,
                "title": pub.title,
                "abstract": pub.abstract,
                "publication_date": pub.publication_date.isoformat() if pub.publication_date else None,
                "journal": pub.journal,
                "citation_count": pub.citation_count,
                "references_list": pub.references_list,
                "source_api": pub.source_api,
                "raw_data": pub.raw_data,
            })

        result = self._client.table(self._table).upsert(rows, on_conflict="author_id,work_id").execute()
        return result.data or []

    def get_by_author_id(self, author_id: int) -> list[dict]:
        result = self._client.table(self._table).select("*").eq("author_id", author_id).execute()
        return result.data or []

    def get_count_by_author_id(self, author_id: int) -> int:
        result = (
            self._client.table(self._table)
            .select("id", count="exact")
            .eq("author_id", author_id)
            .execute()
        )
        return result.count or 0
