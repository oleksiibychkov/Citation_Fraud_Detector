"""Tests for the analysis pipeline orchestrator."""

from unittest.mock import MagicMock

import pytest

from cfd.analysis.pipeline import AnalysisPipeline, AnalysisResult
from cfd.config.settings import Settings
from cfd.data.models import AuthorData, AuthorProfile
from cfd.exceptions import AuthorNotFoundError


@pytest.fixture
def settings():
    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        scopus_api_key="test-key",
    )


@pytest.fixture
def mock_strategy(sample_author_data):
    strategy = MagicMock()
    strategy.collect.return_value = sample_author_data
    return strategy


@pytest.fixture
def pipeline(mock_strategy, settings):
    return AnalysisPipeline(strategy=mock_strategy, settings=settings)


class TestAnalysisPipeline:
    def test_successful_analysis(self, pipeline):
        result = pipeline.analyze("Ivanenko", scopus_id="57200000001")
        assert isinstance(result, AnalysisResult)
        assert result.status == "completed"
        assert result.author_profile.surname == "Ivanenko"
        assert result.fraud_score >= 0.0
        assert result.fraud_score <= 1.0
        assert result.confidence_level in ("normal", "low", "moderate", "high", "critical")
        # SCR, MCR, CB, TA, HTA, RLA, GIC, CV, SBD, ANA, CC, SSD, PB, CPC (+CTX, centrality if graph)
        assert len(result.indicators) >= 14

    def test_insufficient_data(self, settings):
        """Author with too few publications/citations should get insufficient_data status."""
        profile = AuthorProfile(
            scopus_id="1", surname="NewAuthor", full_name="New Author",
            publication_count=2, citation_count=3, h_index=1, source_api="test",
        )
        data = AuthorData(profile=profile, publications=[], citations=[])
        strategy = MagicMock()
        strategy.collect.return_value = data
        pipeline = AnalysisPipeline(strategy=strategy, settings=settings)

        result = pipeline.analyze("NewAuthor", scopus_id="1")
        assert result.status == "insufficient_data"
        assert len(result.warnings) > 0

    def test_author_not_found(self, settings):
        strategy = MagicMock()
        strategy.collect.side_effect = AuthorNotFoundError("Not found")
        pipeline = AnalysisPipeline(strategy=strategy, settings=settings)

        with pytest.raises(AuthorNotFoundError):
            pipeline.analyze("Unknown", scopus_id="99999999999")

    def test_with_db_repos(self, mock_strategy, settings):
        author_repo = MagicMock()
        author_repo.upsert.return_value = {"id": 42}
        pub_repo = MagicMock()
        cit_repo = MagicMock()
        ind_repo = MagicMock()
        score_repo = MagicMock()

        pipeline = AnalysisPipeline(
            strategy=mock_strategy, settings=settings,
            author_repo=author_repo, pub_repo=pub_repo,
            cit_repo=cit_repo, ind_repo=ind_repo, score_repo=score_repo,
        )
        result = pipeline.analyze("Ivanenko", scopus_id="57200000001")

        assert result.status == "completed"
        author_repo.upsert.assert_called_once()
        pub_repo.upsert_many.assert_called_once()
        cit_repo.upsert_many.assert_called_once()
        ind_repo.save_many.assert_called_once()
        score_repo.save.assert_called_once()

    def test_db_failure_graceful(self, mock_strategy, settings):
        """Pipeline should work even if DB operations fail."""
        author_repo = MagicMock()
        author_repo.upsert.side_effect = Exception("DB error")

        pipeline = AnalysisPipeline(
            strategy=mock_strategy, settings=settings,
            author_repo=author_repo,
        )
        result = pipeline.analyze("Ivanenko", scopus_id="57200000001")
        assert result.status == "completed"

    def test_indicators_computed(self, pipeline):
        result = pipeline.analyze("Ivanenko", orcid="0000-0002-1234-5678")
        indicator_types = [ind.indicator_type for ind in result.indicators]
        assert "SCR" in indicator_types
        assert "MCR" in indicator_types
        assert "CB" in indicator_types
        assert "TA" in indicator_types
        assert "HTA" in indicator_types
        assert "CV" in indicator_types
        assert "SBD" in indicator_types
        assert "CTX" in indicator_types
        assert "ANA" in indicator_types
        assert "CC" in indicator_types
        assert "SSD" in indicator_types
        assert "PB" in indicator_types
        assert "CPC" in indicator_types
