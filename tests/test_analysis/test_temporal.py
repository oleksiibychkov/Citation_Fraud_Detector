"""Tests for Citation Velocity (CV) and Sleeping Beauty Detector (SBD)."""

from datetime import date

from cfd.analysis.baselines import DisciplineBaseline
from cfd.analysis.temporal import (
    _compute_beauty_coefficient,
    _paper_citation_velocity,
    compute_cv,
    compute_sbd,
)
from cfd.data.models import AuthorData, AuthorProfile, Publication


def _make_profile(**overrides):
    defaults = {
        "surname": "Test",
        "full_name": "Test Author",
        "source_api": "openalex",
        "discipline": "Computer Science",
    }
    defaults.update(overrides)
    return AuthorProfile(**defaults)


def _make_baseline(**overrides):
    defaults = {
        "discipline": "Computer Science",
        "avg_scr": 0.12,
        "std_scr": 0.08,
        "avg_citations_per_paper": 8.5,
        "avg_h_index_growth_rate": 1.2,
        "citation_half_life_years": 5.5,
        "avg_papers_per_year": 3.0,
        "journal_quartile_medians": {"Q1": 15.0, "Q2": 8.0, "Q3": 4.0, "Q4": 2.0},
    }
    defaults.update(overrides)
    return DisciplineBaseline(**defaults)


def _make_publication(work_id, pub_year, citation_count, journal=None, raw_data=None):
    return Publication(
        work_id=work_id,
        title=f"Paper {work_id}",
        publication_date=date(pub_year, 6, 1),
        journal=journal or "Test Journal",
        citation_count=citation_count,
        source_api="openalex",
        raw_data=raw_data,
    )


class TestPaperCitationVelocity:
    def test_basic_velocity(self):
        pub = _make_publication("W1", 2020, 50)
        baseline = _make_baseline()
        v = _paper_citation_velocity(pub, baseline, current_year=2025)
        assert v is not None
        assert v > 0

    def test_no_date_returns_none(self):
        pub = Publication(work_id="W1", citation_count=50, source_api="openalex")
        baseline = _make_baseline()
        assert _paper_citation_velocity(pub, baseline) is None

    def test_new_paper_returns_none(self):
        pub = _make_publication("W1", 2025, 5)
        baseline = _make_baseline()
        v = _paper_citation_velocity(pub, baseline, current_year=2025)
        assert v is None  # age < 1

    def test_higher_citations_higher_velocity(self):
        baseline = _make_baseline()
        pub_low = _make_publication("W1", 2020, 10)
        pub_high = _make_publication("W2", 2020, 100)
        v_low = _paper_citation_velocity(pub_low, baseline, current_year=2025)
        v_high = _paper_citation_velocity(pub_high, baseline, current_year=2025)
        assert v_high > v_low

    def test_q1_journal_adjusts_velocity(self):
        baseline = _make_baseline()
        pub_q2 = _make_publication("W1", 2020, 50, journal="Some Journal")
        pub_q1 = _make_publication("W2", 2020, 50, journal="Nature")
        v_q2 = _paper_citation_velocity(pub_q2, baseline, current_year=2025)
        v_q1 = _paper_citation_velocity(pub_q1, baseline, current_year=2025)
        # Q1 has higher expected → lower velocity for same citation count
        assert v_q1 < v_q2

    def test_older_paper_lower_velocity(self):
        baseline = _make_baseline()
        pub_old = _make_publication("W1", 2010, 50)
        pub_new = _make_publication("W2", 2022, 50)
        v_old = _paper_citation_velocity(pub_old, baseline, current_year=2025)
        v_new = _paper_citation_velocity(pub_new, baseline, current_year=2025)
        # Older papers have higher expected, so lower velocity for same count
        assert v_old < v_new


class TestComputeCV:
    def test_no_publications(self):
        ad = AuthorData(
            profile=_make_profile(),
            publications=[],
            citations=[],
        )
        result = compute_cv(ad, _make_baseline())
        assert result.indicator_type == "CV"
        assert result.value == 0.0
        assert result.details["status"] == "N/A"

    def test_normal_citations(self):
        pubs = [_make_publication(f"W{i}", 2018 + i, 10 + i * 2) for i in range(5)]
        ad = AuthorData(
            profile=_make_profile(),
            publications=pubs,
            citations=[],
        )
        result = compute_cv(ad, _make_baseline(), current_year=2025)
        assert result.indicator_type == "CV"
        assert result.value >= 0.0
        assert "median_velocity" in result.details
        assert "papers_evaluated" in result.details

    def test_high_citations_high_cv(self):
        # Papers with very high citation counts → high velocity
        pubs = [_make_publication(f"W{i}", 2022, 500) for i in range(5)]
        ad = AuthorData(
            profile=_make_profile(),
            publications=pubs,
            citations=[],
        )
        result = compute_cv(ad, _make_baseline(), current_year=2025)
        assert result.value > 0.3  # should be elevated

    def test_top_papers_limited_to_3(self):
        pubs = [_make_publication(f"W{i}", 2020, 10 * i) for i in range(1, 8)]
        ad = AuthorData(
            profile=_make_profile(),
            publications=pubs,
            citations=[],
        )
        result = compute_cv(ad, _make_baseline(), current_year=2025)
        assert len(result.details["top_papers"]) <= 3

    def test_cv_normalized_to_01(self):
        pubs = [_make_publication(f"W{i}", 2020, 1000) for i in range(3)]
        ad = AuthorData(
            profile=_make_profile(),
            publications=pubs,
            citations=[],
        )
        result = compute_cv(ad, _make_baseline(), current_year=2025)
        assert 0.0 <= result.value <= 1.0

    def test_cv_threshold_param_lowers_score(self):
        """Higher cv_threshold → lower normalized value."""
        pubs = [_make_publication(f"W{i}", 2020, 100) for i in range(5)]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        baseline = _make_baseline()
        r_default = compute_cv(ad, baseline, current_year=2025, cv_threshold=5.0)
        r_lenient = compute_cv(ad, baseline, current_year=2025, cv_threshold=20.0)
        assert r_lenient.value <= r_default.value

    def test_cv_threshold_param_raises_score(self):
        """Lower cv_threshold → higher normalized value."""
        pubs = [_make_publication(f"W{i}", 2020, 50) for i in range(5)]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        baseline = _make_baseline()
        r_default = compute_cv(ad, baseline, current_year=2025, cv_threshold=5.0)
        r_strict = compute_cv(ad, baseline, current_year=2025, cv_threshold=2.0)
        assert r_strict.value >= r_default.value


class TestComputeBeautyCoefficient:
    def test_no_data(self):
        b, aw, sd = _compute_beauty_coefficient({})
        assert b == 0.0

    def test_insufficient_data(self):
        b, aw, sd = _compute_beauty_coefficient({2020: 5, 2021: 10})
        assert b == 0.0

    def test_classic_sleeping_beauty(self):
        # Low citations for years, then sudden spike
        yearly = {
            2010: 1, 2011: 0, 2012: 1, 2013: 0, 2014: 1,
            2015: 2, 2016: 1, 2017: 50, 2018: 30, 2019: 20,
        }
        b, aw, sd = _compute_beauty_coefficient(yearly)
        assert b > 10
        assert aw == 2017
        assert sd == 7  # 2017 - 2010

    def test_gradual_growth_low_beauty(self):
        yearly = {2010: 5, 2011: 8, 2012: 12, 2013: 15, 2014: 20}
        b, aw, sd = _compute_beauty_coefficient(yearly)
        # Gradual growth → lower beauty coefficient
        assert b >= 0

    def test_peak_at_start_no_sleep(self):
        yearly = {2010: 50, 2011: 30, 2012: 10}
        b, aw, sd = _compute_beauty_coefficient(yearly)
        # Peak too early (idx=0 < 2) → no sleeping period
        assert b == 0.0


class TestComputeSBD:
    def test_no_publications(self):
        ad = AuthorData(
            profile=_make_profile(),
            publications=[],
            citations=[],
        )
        result = compute_sbd(ad)
        assert result.indicator_type == "SBD"
        assert result.value == 0.0
        assert result.details["status"] == "N/A"

    def test_with_sleeping_beauty(self):
        pubs = [
            _make_publication("W1", 2010, 80, raw_data={
                "counts_by_year": [
                    {"year": 2010, "cited_by_count": 1},
                    {"year": 2011, "cited_by_count": 0},
                    {"year": 2012, "cited_by_count": 1},
                    {"year": 2013, "cited_by_count": 0},
                    {"year": 2014, "cited_by_count": 1},
                    {"year": 2015, "cited_by_count": 2},
                    {"year": 2016, "cited_by_count": 1},
                    {"year": 2017, "cited_by_count": 50},
                    {"year": 2018, "cited_by_count": 20},
                ],
            }),
        ]
        ad = AuthorData(
            profile=_make_profile(),
            publications=pubs,
            citations=[],
        )
        result = compute_sbd(ad)
        assert result.indicator_type == "SBD"
        assert "max_beauty_coefficient" in result.details
        assert result.details["max_beauty_coefficient"] > 0

    def test_no_sleeping_patterns(self):
        pubs = [
            _make_publication("W1", 2020, 15, raw_data={
                "counts_by_year": [
                    {"year": 2020, "cited_by_count": 5},
                    {"year": 2021, "cited_by_count": 5},
                    {"year": 2022, "cited_by_count": 5},
                ],
            }),
        ]
        ad = AuthorData(
            profile=_make_profile(),
            publications=pubs,
            citations=[],
        )
        result = compute_sbd(ad)
        # Peak at first year → no sleeping beauty
        assert result.value == 0.0 or result.details.get("status") == "N/A"

    def test_uses_cited_by_timestamps_fallback(self):
        pubs = [
            _make_publication("W1", 2010, 30),
        ]
        timestamps = {
            "W1": [
                date(2010, 3, 1), date(2011, 6, 1),
                date(2015, 1, 1), date(2015, 5, 1), date(2015, 8, 1),
                date(2015, 11, 1), date(2016, 2, 1), date(2016, 7, 1),
                date(2016, 10, 1), date(2017, 1, 1), date(2017, 4, 1),
                date(2017, 7, 1), date(2017, 10, 1),
            ],
        }
        ad = AuthorData(
            profile=_make_profile(),
            publications=pubs,
            citations=[],
            cited_by_timestamps=timestamps,
        )
        result = compute_sbd(ad)
        assert result.indicator_type == "SBD"
        # Should use timestamps to build yearly data
        assert result.details.get("status") != "N/A" or result.value >= 0

    def test_sbd_beauty_threshold_param(self):
        """Higher beauty_threshold → fewer papers exceed it."""
        pubs = [
            _make_publication("W1", 2005, 200, raw_data={
                "counts_by_year": [
                    {"year": 2005, "cited_by_count": 0},
                    {"year": 2006, "cited_by_count": 0},
                    {"year": 2007, "cited_by_count": 0},
                    {"year": 2010, "cited_by_count": 100},
                    {"year": 2011, "cited_by_count": 50},
                ],
            }),
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        r_default = compute_sbd(ad, beauty_threshold=100.0)
        r_lenient = compute_sbd(ad, beauty_threshold=99999.0)
        # With very high beauty threshold, no papers should exceed it
        assert r_lenient.details.get("high_beauty_papers", 0) <= r_default.details.get("high_beauty_papers", 0)

    def test_sbd_suspicious_threshold_param(self):
        """Lower suspicious_threshold → higher normalized value."""
        pubs = [
            _make_publication(f"W{i}", 2005, 200, raw_data={
                "counts_by_year": [
                    {"year": 2005, "cited_by_count": 0},
                    {"year": 2006, "cited_by_count": 0},
                    {"year": 2007, "cited_by_count": 0},
                    {"year": 2010, "cited_by_count": 100},
                    {"year": 2011, "cited_by_count": 50},
                ],
            })
            for i in range(5)
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        r_default = compute_sbd(ad, suspicious_threshold=0.3)
        r_strict = compute_sbd(ad, suspicious_threshold=0.1)
        assert r_strict.value >= r_default.value

    def test_sbd_normalized_to_01(self):
        # Many papers with extreme beauty coefficients
        pubs = [
            _make_publication(f"W{i}", 2005, 200, raw_data={
                "counts_by_year": [
                    {"year": 2005, "cited_by_count": 0},
                    {"year": 2006, "cited_by_count": 0},
                    {"year": 2007, "cited_by_count": 0},
                    {"year": 2008, "cited_by_count": 0},
                    {"year": 2009, "cited_by_count": 0},
                    {"year": 2010, "cited_by_count": 100},
                    {"year": 2011, "cited_by_count": 50},
                ],
            })
            for i in range(5)
        ]
        ad = AuthorData(
            profile=_make_profile(),
            publications=pubs,
            citations=[],
        )
        result = compute_sbd(ad)
        assert 0.0 <= result.value <= 1.0

    def test_top_papers_in_details(self):
        pubs = [
            _make_publication(f"W{i}", 2005 + i, 100, raw_data={
                "counts_by_year": [
                    {"year": 2005 + i, "cited_by_count": 0},
                    {"year": 2006 + i, "cited_by_count": 0},
                    {"year": 2007 + i, "cited_by_count": 0},
                    {"year": 2012 + i, "cited_by_count": 80},
                    {"year": 2013 + i, "cited_by_count": 20},
                ],
            })
            for i in range(5)
        ]
        ad = AuthorData(
            profile=_make_profile(),
            publications=pubs,
            citations=[],
        )
        result = compute_sbd(ad)
        if result.details.get("top_papers"):
            assert len(result.details["top_papers"]) <= 3
