"""Author connections repository."""

from __future__ import annotations

from typing import Any


class AuthorConnectionRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "author_connections"

    def upsert(self, connection_data: dict) -> dict:
        """Upsert an author connection."""
        result = (
            self._client.table(self._table)
            .upsert(connection_data, on_conflict="source_author_id,target_author_id,connection_type")
            .execute()
        )
        data = result.data or []
        return data[0] if data else {}

    def get_by_author(self, author_id: int, limit: int = 100) -> list[dict]:
        """Get all connections for an author (as source or target)."""
        # Get outgoing connections
        result_out = (
            self._client.table(self._table)
            .select("*")
            .eq("source_author_id", author_id)
            .limit(limit)
            .execute()
        )
        # Get incoming connections
        result_in = (
            self._client.table(self._table)
            .select("*")
            .eq("target_author_id", author_id)
            .limit(limit)
            .execute()
        )
        out = result_out.data or []
        inc = result_in.data or []
        return out + inc

    def get_connection_map(self, author_id: int) -> dict:
        """Get a structured connection map for visualization."""
        connections = self.get_by_author(author_id)
        nodes = set()
        edges = []
        for c in connections:
            src = c.get("source_author_id")
            tgt = c.get("target_author_id")
            if src is not None:
                nodes.add(src)
            if tgt is not None:
                nodes.add(tgt)
            edges.append({
                "source": src,
                "target": tgt,
                "type": c.get("connection_type"),
                "strength": c.get("strength", 0),
            })
        return {"nodes": list(nodes), "edges": edges}
