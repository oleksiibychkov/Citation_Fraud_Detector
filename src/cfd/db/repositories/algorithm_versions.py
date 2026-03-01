"""Algorithm version registry repository."""

from __future__ import annotations

from typing import Any


class AlgorithmVersionRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "algorithm_versions"

    def get_by_version(self, version: str) -> dict | None:
        """Get a specific algorithm version record."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("version", version)
            .limit(1)
            .execute()
        )
        data = result.data or []
        return data[0] if data else None

    def get_all(self) -> list[dict]:
        """Get all algorithm versions."""
        result = (
            self._client.table(self._table)
            .select("*")
            .order("release_date", desc=True)
            .execute()
        )
        return result.data or []

    def register(self, version_data: dict) -> dict:
        """Register a new algorithm version."""
        result = (
            self._client.table(self._table)
            .upsert(version_data, on_conflict="version")
            .execute()
        )
        data = result.data or []
        return data[0] if data else {}
