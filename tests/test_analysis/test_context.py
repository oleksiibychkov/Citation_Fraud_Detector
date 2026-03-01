"""Tests for Contextual Anomaly Analysis (CTX)."""

from datetime import date

from cfd.analysis.context import _count_review_articles, contextual_check
from cfd.data.models import AuthorData, AuthorProfile, Publication
from cfd.graph.metrics import IndicatorResult


def _make_profile(**overrides):
    defaults = {
        "surname": "Test",
        "full_name": "Test Author",
        "source_api": "openalex",
        "discipline": "Computer Science",
    }
    defaults.update(overrides)
    return AuthorProfile(**defaults)


def _make_author_data(pubs=None, cits=None):
    return AuthorData(
        profile=_make_profile(),
        publications=pubs or [],
        citations=cits or [],
    )


def _indicator(name, value, details=None):
    return IndicatorResult(name, value, details or {})


class TestContextualCheckTrigger:
    def test_not_triggered_when_all_low(self):
        indicators = {
            "TA": _indicator("TA", 0.1),
            "HTA": _indicator("HTA", 0.1),
            "CB": _indicator("CB", 0.1),
        }
        result = contextual_check(_make_author_data(), indicators)
        assert result.indicator_type == "CTX"
        assert result.value == 0.0
        assert result.details["status"] == "not_triggered"

    def test_triggered_by_ta(self):
        indicators = {
            "TA": _indicator("TA", 0.6),
            "HTA": _indicator("HTA", 0.1),
            "CB": _indicator("CB", 0.1),
        }
        result = contextual_check(_make_author_data(), indicators)
        assert result.value >= 0.0
        assert "TA=" in result.details["trigger_reasons"][0]

    def test_triggered_by_hta(self):
        indicators = {
            "TA": _indicator("TA", 0.1),
            "HTA": _indicator("HTA", 0.5),
            "CB": _indicator("CB", 0.1),
        }
        result = contextual_check(_make_author_data(), indicators)
        assert "HTA=" in result.details["trigger_reasons"][0]

    def test_triggered_by_cb(self):
        indicators = {
            "TA": _indicator("TA", 0.1),
            "HTA": _indicator("HTA", 0.1),
            "CB": _indicator("CB", 0.5),
        }
        result = contextual_check(_make_author_data(), indicators)
        assert "CB=" in result.details["trigger_reasons"][0]

    def test_no_indicators_returns_not_triggered(self):
        result = contextual_check(_make_author_data(), {})
        assert result.value == 0.0
        assert result.details["status"] == "not_triggered"


class TestContextualCheckSignals:
    def test_high_scr_adds_signal(self):
        indicators = {
            "TA": _indicator("TA", 0.6),
            "SCR": _indicator("SCR", 0.4),
        }
        result = contextual_check(_make_author_data(), indicators)
        signal_types = [s["type"] for s in result.details["signals"]]
        assert "high_self_citation" in signal_types

    def test_high_cb_adds_signal(self):
        indicators = {
            "TA": _indicator("TA", 0.6),
            "CB": _indicator("CB", 0.6),
        }
        result = contextual_check(_make_author_data(), indicators)
        signal_types = [s["type"] for s in result.details["signals"]]
        assert "high_citation_bottleneck" in signal_types

    def test_clique_adds_signal(self):
        indicators = {
            "TA": _indicator("TA", 0.6),
            "CLIQUE": _indicator("CLIQUE", 0.5),
        }
        result = contextual_check(_make_author_data(), indicators)
        signal_types = [s["type"] for s in result.details["signals"]]
        assert "clique_involvement" in signal_types

    def test_cv_adds_signal(self):
        indicators = {
            "TA": _indicator("TA", 0.6),
            "CV": _indicator("CV", 0.5),
        }
        result = contextual_check(_make_author_data(), indicators)
        signal_types = [s["type"] for s in result.details["signals"]]
        assert "high_citation_velocity" in signal_types

    def test_sbd_adds_signal(self):
        indicators = {
            "TA": _indicator("TA", 0.6),
            "SBD": _indicator("SBD", 0.4),
        }
        result = contextual_check(_make_author_data(), indicators)
        signal_types = [s["type"] for s in result.details["signals"]]
        assert "sleeping_beauty_pattern" in signal_types

    def test_low_correlation_adds_signal(self):
        indicators = {
            "TA": _indicator("TA", 0.6, {"citation_pub_correlation": 0.1}),
        }
        result = contextual_check(_make_author_data(), indicators)
        signal_types = [s["type"] for s in result.details["signals"]]
        assert "low_citation_pub_correlation" in signal_types

    def test_multiple_signals_increase_score(self):
        indicators_few = {
            "TA": _indicator("TA", 0.6),
            "SCR": _indicator("SCR", 0.4),
        }
        indicators_many = {
            "TA": _indicator("TA", 0.6),
            "SCR": _indicator("SCR", 0.4),
            "CB": _indicator("CB", 0.6),
            "CLIQUE": _indicator("CLIQUE", 0.5),
            "MCR": _indicator("MCR", 0.5),
        }
        r_few = contextual_check(_make_author_data(), indicators_few)
        r_many = contextual_check(_make_author_data(), indicators_many)
        assert r_many.value > r_few.value


class TestContextualCheckMitigations:
    def test_high_review_ratio_mitigates(self):
        pubs = [
            Publication(
                work_id=f"W{i}",
                title="A systematic review of something",
                publication_date=date(2020, 1, 1),
                citation_count=50,
                source_api="openalex",
            )
            for i in range(4)
        ] + [
            Publication(
                work_id="W5",
                title="Normal paper",
                publication_date=date(2020, 1, 1),
                citation_count=10,
                source_api="openalex",
            )
        ]
        ad = _make_author_data(pubs=pubs)

        indicators = {
            "TA": _indicator("TA", 0.6),
            "SCR": _indicator("SCR", 0.4),
            "CB": _indicator("CB", 0.6),
        }
        result = contextual_check(ad, indicators)
        assert result.details["mitigation_factor"] < 1.0
        assert any("review_ratio" in m for m in result.details["mitigations"])

    def test_high_correlation_mitigates(self):
        indicators = {
            "TA": _indicator("TA", 0.6, {"citation_pub_correlation": 0.8}),
            "SCR": _indicator("SCR", 0.4),
        }
        result = contextual_check(_make_author_data(), indicators)
        assert any("correlated" in m for m in result.details["mitigations"])

    def test_view_check_stubbed(self):
        indicators = {
            "TA": _indicator("TA", 0.6),
        }
        result = contextual_check(_make_author_data(), indicators)
        assert result.details["view_check"]["status"] == "unavailable"


class TestContextualCheckNormalization:
    def test_score_bounded_0_1(self):
        # Many signals → should still be capped at 1.0
        indicators = {
            "TA": _indicator("TA", 0.6),
            "SCR": _indicator("SCR", 0.5),
            "CB": _indicator("CB", 0.7),
            "CLIQUE": _indicator("CLIQUE", 0.6),
            "COMMUNITY": _indicator("COMMUNITY", 0.5),
            "MCR": _indicator("MCR", 0.5),
            "CV": _indicator("CV", 0.6),
            "SBD": _indicator("SBD", 0.5),
        }
        result = contextual_check(_make_author_data(), indicators)
        assert 0.0 <= result.value <= 1.0

    def test_custom_threshold(self):
        indicators = {
            "TA": _indicator("TA", 0.6),
            "SCR": _indicator("SCR", 0.4),
        }
        r1 = contextual_check(_make_author_data(), indicators, independent_threshold=1)
        r3 = contextual_check(_make_author_data(), indicators, independent_threshold=5)
        # Lower threshold → higher normalized score for same signal count
        assert r1.value >= r3.value


class TestCountReviewArticles:
    def test_review_by_title(self):
        pubs = [
            Publication(work_id="W1", title="A Review of ML", source_api="openalex", citation_count=10),
            Publication(work_id="W2", title="Survey on AI", source_api="openalex", citation_count=10),
            Publication(work_id="W3", title="Normal paper", source_api="openalex", citation_count=10),
        ]
        ad = _make_author_data(pubs=pubs)
        assert _count_review_articles(ad) == 2

    def test_review_by_raw_data_type(self):
        pubs = [
            Publication(
                work_id="W1", title="Some paper",
                source_api="openalex", citation_count=10,
                raw_data={"type": "review"},
            ),
        ]
        ad = _make_author_data(pubs=pubs)
        assert _count_review_articles(ad) >= 1

    def test_no_reviews(self):
        pubs = [
            Publication(work_id="W1", title="Normal paper", source_api="openalex", citation_count=10),
        ]
        ad = _make_author_data(pubs=pubs)
        assert _count_review_articles(ad) == 0

    def test_no_title_skipped(self):
        pubs = [
            Publication(work_id="W1", source_api="openalex", citation_count=10),
        ]
        ad = _make_author_data(pubs=pubs)
        assert _count_review_articles(ad) == 0
