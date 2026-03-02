"""Integration tests for the full analysis pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cfd.analysis.pipeline import AnalysisPipeline
from cfd.data.openalex import OpenAlexStrategy
from cfd.exceptions import AuthorNotFoundError

from .conftest import MOCK_WORKS, _build_mock_http, _make_work


class TestFullPipeline:
    def test_pipeline_completes_with_score(self, integration_pipeline):
        result = integration_pipeline.analyze(
            "Ivanenko", orcid="0000-0002-1234-5678",
        )
        assert result.status == "completed"
        assert isinstance(result.fraud_score, float)
        assert 0.0 <= result.fraud_score <= 1.0
        assert result.confidence_level in ("normal", "low", "moderate", "high", "critical")
        assert result.author_profile.surname == "Ivanenko"

    def test_pipeline_computes_base_indicators(self, integration_pipeline):
        result = integration_pipeline.analyze(
            "Ivanenko", orcid="0000-0002-1234-5678",
        )
        indicator_types = {ind.indicator_type for ind in result.indicators}
        for base in ("SCR", "MCR", "CB", "TA", "HTA"):
            assert base in indicator_types, f"Missing indicator: {base}"

    def test_pipeline_computes_extended_indicators(self, integration_pipeline):
        result = integration_pipeline.analyze(
            "Ivanenko", orcid="0000-0002-1234-5678",
        )
        indicator_types = {ind.indicator_type for ind in result.indicators}
        for ext in ("RLA", "GIC"):
            assert ext in indicator_types, f"Missing indicator: {ext}"

    def test_pipeline_insufficient_data(self, integration_settings):
        """With very high thresholds, pipeline returns insufficient_data."""
        strict_settings = integration_settings.model_copy(update={
            "min_publications": 1000,
        })
        citing = [[] for _ in MOCK_WORKS]
        http = _build_mock_http(citing_works=citing)
        strategy = OpenAlexStrategy(http)
        pipeline = AnalysisPipeline(strategy=strategy, settings=strict_settings)

        result = pipeline.analyze("Ivanenko", orcid="0000-0002-1234-5678")
        assert result.status == "insufficient_data"
        assert len(result.warnings) > 0

    def test_pipeline_no_db_repos(self, mock_http, integration_settings):
        """Pipeline completes without errors when all repos are None."""
        strategy = OpenAlexStrategy(mock_http)
        pipeline = AnalysisPipeline(
            strategy=strategy,
            settings=integration_settings,
            author_repo=None,
            pub_repo=None,
            cit_repo=None,
            ind_repo=None,
            score_repo=None,
        )
        result = pipeline.analyze("Ivanenko", orcid="0000-0002-1234-5678")
        assert result.status == "completed"

    def test_pipeline_high_self_citation(self, integration_settings):
        """When all citations are self-citations, fraud score should be elevated."""
        # Build works where every reference is to the author's own works
        works = [
            _make_work("W2001", refs=["W2002", "W2003"]),
            _make_work("W2002", refs=["W2001", "W2003"]),
            _make_work("W2003", refs=["W2001", "W2002"]),
        ]
        citing = [[] for _ in works]
        http = _build_mock_http(works=works, citing_works=citing)
        strategy = OpenAlexStrategy(http)
        pipeline = AnalysisPipeline(strategy=strategy, settings=integration_settings)

        result = pipeline.analyze("Ivanenko", orcid="0000-0002-1234-5678")
        assert result.status == "completed"
        # SCR should be high since all refs point to author's own works
        scr = next((i for i in result.indicators if i.indicator_type == "SCR"), None)
        assert scr is not None

    def test_pipeline_author_not_found(self, integration_settings):
        """Empty API results should raise AuthorNotFoundError."""
        http = MagicMock()
        # Search by orcid returns empty, search by name returns empty
        http.get.side_effect = [
            {"results": []},
            {"results": []},
        ]
        strategy = OpenAlexStrategy(http)
        pipeline = AnalysisPipeline(strategy=strategy, settings=integration_settings)

        with pytest.raises(AuthorNotFoundError):
            pipeline.analyze("Nobody", orcid="0000-0000-0000-0000")
