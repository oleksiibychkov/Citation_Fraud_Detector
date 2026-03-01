"""Author repository for Supabase CRUD operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cfd.data.models import AuthorProfile


class AuthorRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "authors"

    def upsert(self, profile: AuthorProfile) -> dict:
        """Insert or update author. Returns the stored record."""
        data = {
            "surname": profile.surname,
            "full_name": profile.full_name,
            "display_name_variants": profile.display_name_variants,
            "institution": profile.institution,
            "discipline": profile.discipline,
            "h_index": profile.h_index,
            "publication_count": profile.publication_count,
            "citation_count": profile.citation_count,
            "source_api": profile.source_api,
            "raw_data": profile.raw_data,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if profile.scopus_id:
            data["scopus_id"] = profile.scopus_id
        if profile.orcid:
            data["orcid"] = profile.orcid
        if profile.openalex_id:
            data["openalex_id"] = profile.openalex_id

        # Determine upsert conflict column
        if profile.scopus_id:
            result = self._client.table(self._table).upsert(data, on_conflict="scopus_id").execute()
        elif profile.orcid:
            result = self._client.table(self._table).upsert(data, on_conflict="orcid").execute()
        else:
            result = self._client.table(self._table).insert(data).execute()

        return result.data[0] if result.data else data

    def get_by_scopus_id(self, scopus_id: str) -> dict | None:
        result = self._client.table(self._table).select("*").eq("scopus_id", scopus_id).execute()
        return result.data[0] if result.data else None

    def get_by_orcid(self, orcid: str) -> dict | None:
        result = self._client.table(self._table).select("*").eq("orcid", orcid).execute()
        return result.data[0] if result.data else None

    def get_by_id(self, author_id: int) -> dict | None:
        result = self._client.table(self._table).select("*").eq("id", author_id).execute()
        return result.data[0] if result.data else None
