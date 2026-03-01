"""Discipline baselines repository."""

from __future__ import annotations

from typing import Any


class DisciplineBaselineRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "discipline_baselines"

    def get_by_discipline(self, discipline: str) -> dict | None:
        """Get baseline for a specific discipline."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("discipline", discipline)
            .limit(1)
            .execute()
        )
        data = result.data or []
        return data[0] if data else None

    def get_all(self) -> list[dict]:
        """Get all discipline baselines."""
        result = self._client.table(self._table).select("*").execute()
        return result.data or []

    def upsert(self, baseline: dict) -> dict:
        """Upsert a discipline baseline."""
        result = (
            self._client.table(self._table)
            .upsert(baseline, on_conflict="discipline")
            .execute()
        )
        data = result.data or []
        return data[0] if data else {}
