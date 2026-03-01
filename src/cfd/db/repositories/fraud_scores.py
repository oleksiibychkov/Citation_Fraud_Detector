"""Fraud score repository for Supabase CRUD operations."""

from __future__ import annotations

from typing import Any


class FraudScoreRepository:
    def __init__(self, supabase_client: Any):
        self._client = supabase_client
        self._table = "fraud_scores"

    def save(
        self,
        author_id: int,
        score: float,
        confidence_level: str,
        indicator_weights: dict,
        indicator_values: dict,
        triggered_indicators: list[str],
        status: str = "completed",
        algorithm_version: str = "1.0.0",
    ) -> dict:
        """Save a fraud score result."""
        data = {
            "author_id": author_id,
            "score": score,
            "confidence_level": confidence_level,
            "indicator_weights": indicator_weights,
            "indicator_values": indicator_values,
            "triggered_indicators": triggered_indicators,
            "status": status,
            "algorithm_version": algorithm_version,
        }
        result = self._client.table(self._table).insert(data).execute()
        return result.data[0] if result.data else data

    def get_latest_by_author(self, author_id: int) -> dict | None:
        """Get the most recent fraud score for an author."""
        result = (
            self._client.table(self._table)
            .select("*")
            .eq("author_id", author_id)
            .order("calculated_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_all_ranked(self, limit: int = 100) -> list[dict]:
        """Get all fraud scores ranked by score descending (anti-rating)."""
        result = (
            self._client.table(self._table)
            .select("*")
            .order("score", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
