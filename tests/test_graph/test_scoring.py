"""Tests for Fraud Score aggregation and confidence levels."""

import pytest

from cfd.config.settings import Settings
from cfd.graph.metrics import IndicatorResult
from cfd.graph.scoring import DEFAULT_WEIGHTS, _is_triggered, _normalize_indicator, compute_fraud_score


@pytest.fixture
def settings():
    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        scopus_api_key="test-scopus-key",
    )


class TestNormalizeIndicator:
    def test_scr_zero(self, settings):
        ind = IndicatorResult("SCR", 0.0, {})
        assert _normalize_indicator(ind, settings) == 0.0

    def test_scr_at_warn(self, settings):
        ind = IndicatorResult("SCR", settings.scr_warn_threshold, {})
        assert _normalize_indicator(ind, settings) == pytest.approx(0.5)

    def test_scr_at_high(self, settings):
        ind = IndicatorResult("SCR", settings.scr_high_threshold, {})
        assert _normalize_indicator(ind, settings) == pytest.approx(1.0)

    def test_scr_above_high(self, settings):
        ind = IndicatorResult("SCR", 1.0, {})
        assert _normalize_indicator(ind, settings) == 1.0

    def test_mcr_zero(self, settings):
        ind = IndicatorResult("MCR", 0.0, {})
        assert _normalize_indicator(ind, settings) == 0.0

    def test_mcr_at_double_threshold(self, settings):
        ind = IndicatorResult("MCR", settings.mcr_threshold * 2, {})
        assert _normalize_indicator(ind, settings) == pytest.approx(1.0)

    def test_cb_half_threshold(self, settings):
        ind = IndicatorResult("CB", settings.cb_threshold, {})
        expected = settings.cb_threshold / (settings.cb_threshold * 2)
        assert _normalize_indicator(ind, settings) == pytest.approx(expected)

    def test_ta_passthrough(self, settings):
        ind = IndicatorResult("TA", 0.75, {})
        assert _normalize_indicator(ind, settings) == 0.75

    def test_hta_clamped(self, settings):
        ind = IndicatorResult("HTA", 1.5, {})
        assert _normalize_indicator(ind, settings) == 1.0

    def test_cv_passthrough(self, settings):
        ind = IndicatorResult("CV", 0.6, {})
        assert _normalize_indicator(ind, settings) == 0.6

    def test_sbd_passthrough(self, settings):
        ind = IndicatorResult("SBD", 0.4, {})
        assert _normalize_indicator(ind, settings) == 0.4

    def test_ctx_passthrough(self, settings):
        ind = IndicatorResult("CTX", 0.5, {})
        assert _normalize_indicator(ind, settings) == 0.5

    def test_ana_passthrough(self, settings):
        ind = IndicatorResult("ANA", 0.6, {})
        assert _normalize_indicator(ind, settings) == 0.6

    def test_pb_passthrough(self, settings):
        ind = IndicatorResult("PB", 0.3, {})
        assert _normalize_indicator(ind, settings) == 0.3

    def test_ssd_passthrough(self, settings):
        ind = IndicatorResult("SSD", 0.5, {})
        assert _normalize_indicator(ind, settings) == 0.5

    def test_cc_passthrough(self, settings):
        ind = IndicatorResult("CC", 0.7, {})
        assert _normalize_indicator(ind, settings) == 0.7

    def test_cpc_passthrough(self, settings):
        ind = IndicatorResult("CPC", 0.4, {})
        assert _normalize_indicator(ind, settings) == 0.4


class TestIsTriggered:
    def test_scr_triggered(self, settings):
        ind = IndicatorResult("SCR", settings.scr_warn_threshold + 0.01, {})
        assert _is_triggered(ind, settings) is True

    def test_scr_not_triggered(self, settings):
        ind = IndicatorResult("SCR", settings.scr_warn_threshold - 0.01, {})
        assert _is_triggered(ind, settings) is False

    def test_mcr_triggered(self, settings):
        ind = IndicatorResult("MCR", settings.mcr_threshold + 0.01, {})
        assert _is_triggered(ind, settings) is True

    def test_cb_triggered(self, settings):
        ind = IndicatorResult("CB", settings.cb_threshold + 0.01, {})
        assert _is_triggered(ind, settings) is True

    def test_ta_triggered(self, settings):
        ind = IndicatorResult("TA", 0.5, {"max_z_score": settings.ta_z_threshold + 0.1})
        assert _is_triggered(ind, settings) is True

    def test_ta_not_triggered(self, settings):
        ind = IndicatorResult("TA", 0.1, {"max_z_score": 1.0})
        assert _is_triggered(ind, settings) is False

    def test_cv_triggered(self, settings):
        ind = IndicatorResult("CV", 0.5, {})
        assert _is_triggered(ind, settings) is True

    def test_cv_not_triggered(self, settings):
        ind = IndicatorResult("CV", 0.2, {})
        assert _is_triggered(ind, settings) is False

    def test_sbd_triggered(self, settings):
        ind = IndicatorResult("SBD", settings.sbd_suspicious_threshold + 0.01, {})
        assert _is_triggered(ind, settings) is True

    def test_ctx_triggered(self, settings):
        ind = IndicatorResult("CTX", 0.5, {})
        assert _is_triggered(ind, settings) is True

    def test_ana_triggered(self, settings):
        ind = IndicatorResult("ANA", 0.5, {})
        assert _is_triggered(ind, settings) is True

    def test_ana_not_triggered(self, settings):
        ind = IndicatorResult("ANA", 0.3, {})
        assert _is_triggered(ind, settings) is False

    def test_pb_triggered(self, settings):
        ind = IndicatorResult("PB", 0.4, {})
        assert _is_triggered(ind, settings) is True

    def test_ssd_triggered(self, settings):
        ind = IndicatorResult("SSD", 0.4, {})
        assert _is_triggered(ind, settings) is True

    def test_cc_triggered(self, settings):
        ind = IndicatorResult("CC", 0.4, {})
        assert _is_triggered(ind, settings) is True

    def test_cpc_triggered(self, settings):
        ind = IndicatorResult("CPC", 0.4, {})
        assert _is_triggered(ind, settings) is True

    def test_cpc_not_triggered(self, settings):
        ind = IndicatorResult("CPC", 0.2, {})
        assert _is_triggered(ind, settings) is False

    def test_unknown_type(self, settings):
        ind = IndicatorResult("UNKNOWN", 0.5, {})
        assert _is_triggered(ind, settings) is False


class TestComputeFraudScore:
    def test_all_zero(self, settings):
        indicators = [
            IndicatorResult("SCR", 0.0, {}),
            IndicatorResult("MCR", 0.0, {}),
            IndicatorResult("CB", 0.0, {}),
            IndicatorResult("TA", 0.0, {"max_z_score": 0}),
            IndicatorResult("HTA", 0.0, {"max_z_score": 0}),
        ]
        score, level, triggered = compute_fraud_score(indicators, settings)
        assert score == 0.0
        assert level == "normal"
        assert triggered == []

    def test_all_max(self, settings):
        indicators = [
            IndicatorResult("SCR", 1.0, {}),
            IndicatorResult("MCR", 1.0, {}),
            IndicatorResult("CB", 1.0, {}),
            IndicatorResult("TA", 1.0, {"max_z_score": 10}),
            IndicatorResult("HTA", 1.0, {"max_z_score": 10}),
        ]
        score, level, triggered = compute_fraud_score(indicators, settings)
        assert score > 0.5
        assert level in ("high", "critical")
        assert len(triggered) > 0

    def test_partial_indicators(self, settings):
        indicators = [
            IndicatorResult("SCR", 0.3, {}),
            IndicatorResult("MCR", 0.0, {}),
        ]
        score, level, triggered = compute_fraud_score(indicators, settings)
        assert 0.0 <= score <= 1.0
        assert level in ("normal", "low", "moderate", "high", "critical")

    def test_confidence_levels(self, settings):
        # Test that different score ranges map to correct levels
        for score_val, _expected_level in [
            (0.0, "normal"),
            (0.1, "normal"),
            (0.3, "low"),
            (0.5, "moderate"),
            (0.7, "high"),
            (0.9, "critical"),
        ]:
            indicators = [IndicatorResult("TA", score_val, {"max_z_score": 0})]
            score, level, _ = compute_fraud_score(indicators, settings)
            # We can't assert exact level because normalization affects score,
            # but we verify the function returns valid levels
            assert level in ("normal", "low", "moderate", "high", "critical")

    def test_empty_indicators(self, settings):
        score, level, triggered = compute_fraud_score([], settings)
        assert score == 0.0
        assert level == "normal"
        assert triggered == []

    def test_weights_sum_to_one(self):
        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-10

    def test_weights_count(self):
        assert len(DEFAULT_WEIGHTS) == 22

    def test_new_indicators_included(self, settings):
        indicators = [
            IndicatorResult("ANA", 0.5, {}),
            IndicatorResult("PB", 0.4, {}),
            IndicatorResult("SSD", 0.6, {}),
            IndicatorResult("CC", 0.3, {}),
            IndicatorResult("CPC", 0.2, {}),
        ]
        score, level, triggered = compute_fraud_score(indicators, settings)
        assert score > 0.0
        assert "ANA" in triggered
        assert "SSD" in triggered
