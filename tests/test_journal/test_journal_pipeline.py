"""Tests for journal analysis pipeline and scoring."""

import pytest

from cfd.analysis.journal_pipeline import (
    JOURNAL_THRESHOLDS,
    JOURNAL_WEIGHTS,
    JournalAnalysisResult,
    compute_journal_score,
    get_journal_trigger_threshold,
)
from cfd.data.journal_models import JournalProfile
from cfd.graph.metrics import IndicatorResult


class TestComputeJournalScore:
    def test_all_zero_indicators(self):
        indicators = [
            IndicatorResult("J_SCR", 0.0, {}),
            IndicatorResult("J_MCR", 0.0, {}),
            IndicatorResult("J_TA", 0.0, {}),
        ]
        score, confidence, triggered = compute_journal_score(indicators)
        assert score == 0.0
        assert confidence == "normal"
        assert triggered == []

    def test_single_triggered(self):
        indicators = [
            IndicatorResult("J_SCR", 0.5, {}),  # above 0.25 threshold
            IndicatorResult("J_MCR", 0.1, {}),
            IndicatorResult("J_TA", 0.1, {}),
        ]
        score, confidence, triggered = compute_journal_score(indicators)
        assert "J_SCR" in triggered
        assert score > 0

    def test_tier_elevation_scr_plus_coerce(self):
        """J_SCR + J_COERCE both triggered -> min score 0.4."""
        indicators = [
            IndicatorResult("J_SCR", 0.5, {}),
            IndicatorResult("J_COERCE", 0.5, {}),
        ]
        score, confidence, triggered = compute_journal_score(indicators)
        assert score >= 0.4
        assert "J_SCR" in triggered
        assert "J_COERCE" in triggered

    def test_four_triggered_elevation(self):
        """4+ triggered indicators -> min score 0.6."""
        indicators = [
            IndicatorResult("J_SCR", 0.5, {}),
            IndicatorResult("J_MCR", 0.5, {}),
            IndicatorResult("J_TA", 0.5, {}),
            IndicatorResult("J_HIA", 0.5, {}),
        ]
        score, confidence, triggered = compute_journal_score(indicators)
        assert score >= 0.6
        assert len(triggered) >= 4

    def test_confidence_levels(self):
        # Normal
        indicators = [IndicatorResult("J_SCR", 0.05, {})]
        score, conf, _ = compute_journal_score(indicators)
        assert conf == "normal"

    def test_unknown_indicator_ignored(self):
        indicators = [
            IndicatorResult("UNKNOWN", 0.9, {}),
        ]
        score, confidence, triggered = compute_journal_score(indicators)
        assert score == 0.0
        assert triggered == []


class TestGetJournalTriggerThreshold:
    def test_known_indicators(self):
        for name in JOURNAL_THRESHOLDS:
            threshold = get_journal_trigger_threshold(name)
            assert threshold > 0
            assert threshold <= 1.0

    def test_unknown_indicator(self):
        assert get_journal_trigger_threshold("UNKNOWN") == 0.3

    def test_all_weights_sum(self):
        total = sum(JOURNAL_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01


class TestJournalAnalysisResult:
    def test_defaults(self):
        profile = JournalProfile(openalex_id="S1", display_name="Test")
        r = JournalAnalysisResult(profile=profile)
        assert r.fraud_score == 0.0
        assert r.confidence_level == "normal"
        assert r.status == "completed"
        assert r.indicators == []
        assert r.triggered_indicators == []
        assert r.warnings == []
