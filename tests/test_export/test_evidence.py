"""Tests for evidence collection."""

from unittest.mock import MagicMock

from cfd.analysis.pipeline import AnalysisResult
from cfd.data.models import AuthorData, AuthorProfile
from cfd.export.evidence import collect_evidence, save_evidence
from cfd.graph.metrics import IndicatorResult
from cfd.graph.theorems import TheoremResult


def _make_profile():
    return AuthorProfile(surname="Test", full_name="Test Author", source_api="openalex")


class TestCollectEvidence:
    def test_triggered_indicators(self):
        result = AnalysisResult(
            author_profile=_make_profile(),
            indicators=[
                IndicatorResult("SCR", 0.35, {"self_citations": 10}),
                IndicatorResult("MCR", 0.1, {}),
            ],
            fraud_score=0.4,
            confidence_level="moderate",
            triggered_indicators=["SCR"],
        )
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        evidence = collect_evidence(result, ad)
        # Should have SCR evidence
        indicator_evidence = [e for e in evidence if e["indicator_type"] == "SCR"]
        assert len(indicator_evidence) == 1
        assert indicator_evidence[0]["value"] > 0
        # MCR not triggered, should not be in evidence
        mcr_evidence = [e for e in evidence if e["indicator_type"] == "MCR"]
        assert len(mcr_evidence) == 0

    def test_high_fraud_score_adds_aggregate(self):
        result = AnalysisResult(
            author_profile=_make_profile(),
            indicators=[],
            fraud_score=0.6,
            confidence_level="high",
            triggered_indicators=[],
        )
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        evidence = collect_evidence(result, ad)
        aggregate = [e for e in evidence if e["evidence_type"] == "aggregate"]
        assert len(aggregate) == 1

    def test_theorem_results(self):
        result = AnalysisResult(
            author_profile=_make_profile(),
            indicators=[],
            fraud_score=0.3,
            confidence_level="low",
            triggered_indicators=[],
            theorem_results=[TheoremResult(1, True, {"test": True})],
        )
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        evidence = collect_evidence(result, ad)
        theorem_evidence = [e for e in evidence if e["evidence_type"] == "theorem"]
        assert len(theorem_evidence) == 1

    def test_empty_result(self):
        result = AnalysisResult(
            author_profile=_make_profile(),
            indicators=[],
            fraud_score=0.1,
            confidence_level="normal",
            triggered_indicators=[],
        )
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        evidence = collect_evidence(result, ad)
        assert len(evidence) == 0


class TestSaveEvidence:
    def test_saves_to_repo(self):
        repo = MagicMock()
        evidence = [{"evidence_type": "indicator", "indicator_type": "SCR", "value": 0.35}]
        save_evidence(evidence, repo, author_id=1, algorithm_version="4.0.0")
        repo.save_many.assert_called_once()

    def test_empty_evidence_skipped(self):
        repo = MagicMock()
        save_evidence([], repo, author_id=1, algorithm_version="4.0.0")
        repo.save_many.assert_not_called()

    def test_none_repo_skipped(self):
        save_evidence([{"test": True}], None, author_id=1, algorithm_version="4.0.0")
