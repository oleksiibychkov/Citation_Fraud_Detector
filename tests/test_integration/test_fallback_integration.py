"""Integration tests for FallbackStrategy through the pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cfd.analysis.pipeline import AnalysisPipeline
from cfd.config.settings import Settings
from cfd.data.fallback import FallbackStrategy
from cfd.data.openalex import OpenAlexStrategy
from cfd.exceptions import APIError

from .conftest import MOCK_WORKS, _build_mock_http


@pytest.fixture
def fallback_settings():
    return Settings(
        min_publications=1,
        min_citations=1,
        min_h_index=0,
        supabase_url="",
        supabase_key="",
    )


class TestFallbackIntegration:
    def test_primary_fails_secondary_succeeds(self, fallback_settings):
        """Primary raises APIError on fetch_author → secondary takes over."""
        primary_http = MagicMock()
        primary_http.get.side_effect = APIError("Primary down")

        citing = [[] for _ in MOCK_WORKS]
        secondary_http = _build_mock_http(citing_works=citing)

        primary = OpenAlexStrategy(primary_http)
        secondary = OpenAlexStrategy(secondary_http)
        fallback = FallbackStrategy(primary, secondary)

        pipeline = AnalysisPipeline(strategy=fallback, settings=fallback_settings)
        result = pipeline.analyze("Ivanenko", orcid="0000-0002-1234-5678")
        assert result.status == "completed"
        assert result.author_profile.surname == "Ivanenko"

    def test_publications_failover(self, fallback_settings):
        """Primary works for author, fails on publications → secondary provides pubs."""
        from cfd.data.models import AuthorProfile

        primary = MagicMock()
        secondary = MagicMock()

        profile = AuthorProfile(
            surname="Ivanenko",
            full_name="Oleksandr Ivanenko",
            openalex_id="A100001",
            h_index=15,
            publication_count=50,
            citation_count=500,
            institution="Kyiv National University",
            discipline="Computer Science",
            source_api="openalex",
        )

        primary.fetch_author.return_value = profile
        primary.fetch_publications.side_effect = APIError("Timeout on pubs")
        secondary.fetch_publications.return_value = []
        primary.fetch_citations.return_value = []

        fallback = FallbackStrategy(primary, secondary)
        pipeline = AnalysisPipeline(strategy=fallback, settings=fallback_settings)
        result = pipeline.analyze("Ivanenko", orcid="0000-0002-1234-5678")
        assert result.status == "completed"

    def test_citations_failover(self, fallback_settings):
        """Primary works for author + pubs, fails on citations → secondary provides citations."""
        from cfd.data.models import AuthorProfile

        primary = MagicMock()
        secondary = MagicMock()

        profile = AuthorProfile(
            surname="Ivanenko",
            full_name="Oleksandr Ivanenko",
            openalex_id="A100001",
            h_index=15,
            publication_count=50,
            citation_count=500,
            discipline="Computer Science",
            source_api="openalex",
        )

        primary.fetch_author.return_value = profile
        primary.fetch_publications.return_value = []
        primary.fetch_citations.side_effect = APIError("Citations timeout")
        secondary.fetch_citations.return_value = []

        fallback = FallbackStrategy(primary, secondary)
        pipeline = AnalysisPipeline(strategy=fallback, settings=fallback_settings)
        result = pipeline.analyze("Ivanenko", orcid="0000-0002-1234-5678")
        assert result.status == "completed"

    def test_both_fail(self, fallback_settings):
        """Both primary and secondary fail → error propagates."""
        primary = MagicMock()
        secondary = MagicMock()

        primary.fetch_author.side_effect = APIError("Primary down")
        secondary.fetch_author.side_effect = APIError("Secondary down")

        primary.collect.side_effect = APIError("Primary down")
        secondary.collect.side_effect = APIError("Secondary down")

        fallback = FallbackStrategy(primary, secondary)
        pipeline = AnalysisPipeline(strategy=fallback, settings=fallback_settings)
        with pytest.raises(APIError):
            pipeline.analyze("Nobody", scopus_id="00000000000")
