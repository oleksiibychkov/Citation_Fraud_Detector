"""Peer group repository for Supabase."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PeerGroupRepository:
    """Repository for peer group management."""

    def __init__(self, supabase_client):
        self._client = supabase_client
        self._table = "peer_groups"

    def save(
        self,
        author_id: int,
        peer_author_ids: list[int],
        discipline: str,
        matching_criteria: dict | None = None,
    ) -> dict:
        """Save a peer group."""
        record = {
            "author_id": author_id,
            "peer_author_ids": peer_author_ids,
            "discipline": discipline,
            "matching_criteria": matching_criteria or {},
        }
        result = self._client.table(self._table).upsert(record).execute()
        return result.data[0] if result.data else {}

    def get_by_author_id(self, author_id: int) -> dict | None:
        """Get the latest peer group for an author."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("author_id", author_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def find_peers(
        self,
        discipline: str,
        min_pubs: int = 0,
        max_pubs: int = 10000,
        limit: int = 20,
    ) -> list[dict]:
        """Find potential peer authors matching criteria."""
        result = (
            self._client.table("authors")
            .select("id,surname,full_name,discipline,h_index,publication_count,citation_count")
            .eq("discipline", discipline)
            .gte("publication_count", min_pubs)
            .lte("publication_count", max_pubs)
            .limit(limit)
            .execute()
        )
        return result.data or []
