"""Tests for journal-level citation manipulation indicators."""

from datetime import date

import pytest

from cfd.analysis.journal_indicators import (
    compute_j_cb,
    compute_j_cdf,
    compute_j_coerce,
    compute_j_ec,
    compute_j_growth,
    compute_j_hia,
    compute_j_mcr,
    compute_j_scr,
    compute_j_ta,
)
from cfd.data.journal_models import (
    JournalCitation,
    JournalData,
    JournalProfile,
    JournalWork,
)


def _make_profile(**kwargs):
    defaults = dict(openalex_id="S100", display_name="Test Journal")
    defaults.update(kwargs)
    return JournalProfile(**defaults)


def _make_data(
    profile=None,
    works=None,
    citations=None,
    citing_journals=None,
):
    return JournalData(
        profile=profile or _make_profile(),
        works=works or [],
        citations=citations or [],
        citing_journals=citing_journals or {},
    )


# ===== J_SCR =====


class TestJSCR:
    def test_no_citations(self):
        result = compute_j_scr(_make_data())
        assert result.indicator_type == "J_SCR"
        assert result.value == 0.0

    def test_all_self_citations(self):
        cits = [
            JournalCitation(source_work_id="W1", target_work_id="W2", is_self_citation=True),
            JournalCitation(source_work_id="W3", target_work_id="W4", is_self_citation=True),
        ]
        result = compute_j_scr(_make_data(citations=cits))
        assert result.value == 1.0

    def test_mixed_citations(self):
        cits = [
            JournalCitation(source_work_id="W1", target_work_id="W2", is_self_citation=True),
            JournalCitation(source_work_id="W3", target_work_id="W4", is_self_citation=False),
            JournalCitation(source_work_id="W5", target_work_id="W6", is_self_citation=False),
            JournalCitation(source_work_id="W7", target_work_id="W8", is_self_citation=False),
        ]
        result = compute_j_scr(_make_data(citations=cits))
        assert result.value == pytest.approx(0.25)
        assert result.details["self_citations"] == 1
        assert result.details["total_citations"] == 4

    def test_no_self_citations(self):
        cits = [
            JournalCitation(source_work_id="W1", target_work_id="W2", is_self_citation=False),
            JournalCitation(source_work_id="W3", target_work_id="W4", is_self_citation=False),
        ]
        result = compute_j_scr(_make_data(citations=cits))
        assert result.value == 0.0


# ===== J_MCR =====


class TestJMCR:
    def test_no_citations(self):
        result = compute_j_mcr(_make_data())
        assert result.value == 0.0

    def test_single_dominant_source(self):
        cits = [
            JournalCitation(source_work_id="W1", target_work_id="W2", source_journal_id="S200", is_self_citation=False),
            JournalCitation(source_work_id="W3", target_work_id="W4", source_journal_id="S200", is_self_citation=False),
            JournalCitation(source_work_id="W5", target_work_id="W6", source_journal_id="S300", is_self_citation=False),
        ]
        result = compute_j_mcr(_make_data(citations=cits))
        assert result.value == pytest.approx(2 / 3)
        assert result.details["top_citing_journal"] == "S200"

    def test_excludes_self_journal(self):
        """Self-citations (same journal) should be excluded from MCR."""
        cits = [
            JournalCitation(source_work_id="W1", target_work_id="W2", source_journal_id="S100", is_self_citation=True),
            JournalCitation(source_work_id="W3", target_work_id="W4", source_journal_id="S200", is_self_citation=False),
        ]
        result = compute_j_mcr(_make_data(citations=cits))
        assert result.value == 1.0  # S200 is the only external source


# ===== J_TA =====


class TestJTA:
    def test_insufficient_data(self):
        result = compute_j_ta(_make_data())
        assert result.value == 0.0

    def test_no_variance(self):
        profile = _make_profile(counts_by_year=[
            {"year": 2020, "cited_by_count": 100},
            {"year": 2021, "cited_by_count": 100},
            {"year": 2022, "cited_by_count": 100},
        ])
        result = compute_j_ta(_make_data(profile=profile))
        assert result.value == 0.0

    def test_detects_spike(self):
        profile = _make_profile(counts_by_year=[
            {"year": 2018, "cited_by_count": 100},
            {"year": 2019, "cited_by_count": 110},
            {"year": 2020, "cited_by_count": 105},
            {"year": 2021, "cited_by_count": 95},
            {"year": 2022, "cited_by_count": 500},  # spike
        ])
        result = compute_j_ta(_make_data(profile=profile))
        assert result.value > 0.3
        assert result.details["spike_year"] == 2022


# ===== J_HIA =====


class TestJHIA:
    def test_no_h_index(self):
        result = compute_j_hia(_make_data())
        assert result.value == 0.0

    def test_normal_h_index(self):
        # h=10, cited=100, works=50 -> expected_h=10 -> ratio~1.0 -> no anomaly
        profile = _make_profile(h_index=10, cited_by_count=100, works_count=50)
        result = compute_j_hia(_make_data(profile=profile))
        assert result.value == 0.0  # ratio ~1.0 < 1.5, no anomaly

    def test_suspicious_h_index(self):
        # h=50, cited=100, works=50 -> expected_h=10 -> ratio=5.0 -> high anomaly
        profile = _make_profile(h_index=50, cited_by_count=100, works_count=50)
        result = compute_j_hia(_make_data(profile=profile))
        assert result.value > 0.5


# ===== J_CDF =====


class TestJCDF:
    def test_no_works(self):
        result = compute_j_cdf(_make_data())
        assert result.value == 0.0

    def test_all_zero_citations(self):
        works = [JournalWork(work_id=f"W{i}", cited_by_count=0) for i in range(10)]
        result = compute_j_cdf(_make_data(works=works))
        assert result.value == 0.0

    def test_natural_power_law(self):
        """Power-law distribution (normal) should have low anomaly score."""
        # Realistic power law: 200, 50, 20, 10, 5, 3, 2, 1, 1, 0
        citations = [200, 50, 20, 10, 5, 3, 2, 1, 1, 0]
        works = [JournalWork(work_id=f"W{i}", cited_by_count=c) for i, c in enumerate(citations)]
        result = compute_j_cdf(_make_data(works=works))
        # High Gini (power-law like) -> low anomaly
        assert result.value < 0.3

    def test_uniform_distribution_suspicious(self):
        """Perfectly uniform citations -> suspicious (low Gini)."""
        works = [JournalWork(work_id=f"W{i}", cited_by_count=10) for i in range(20)]
        result = compute_j_cdf(_make_data(works=works))
        # Gini ~0 -> high anomaly
        assert result.value > 0.3


# ===== J_COERCE =====


class TestJCoerce:
    def test_no_citations(self):
        result = compute_j_coerce(_make_data())
        assert result.value == 0.0

    def test_no_references(self):
        cits = [JournalCitation(source_work_id="W1", target_work_id="W2", is_self_citation=False)]
        result = compute_j_coerce(_make_data(citations=cits))
        assert result.value == 0.0

    def test_high_self_reference(self):
        # Works that reference each other (same journal)
        works = [
            JournalWork(work_id="W1", references_list=["W2", "W3"]),
            JournalWork(work_id="W2", references_list=["W1"]),
            JournalWork(work_id="W3", references_list=["W1", "W2"]),
        ]
        cits = [
            JournalCitation(
                source_work_id="W1", target_work_id="W2",
                is_self_citation=True,
                citation_date=date(2025, 6, 1),
            ),
        ]
        result = compute_j_coerce(_make_data(works=works, citations=cits))
        assert result.value > 0  # Some self-reference detected


# ===== J_EC =====


class TestJEC:
    def test_no_works(self):
        result = compute_j_ec(_make_data())
        assert result.value == 0.0

    def test_no_authors(self):
        works = [JournalWork(work_id="W1")]
        result = compute_j_ec(_make_data(works=works))
        assert result.value == 0.0

    def test_diverse_authors(self):
        """Many unique authors -> low concentration."""
        works = [
            JournalWork(
                work_id=f"W{i}",
                authors=[{"author_id": f"A{i}", "display_name": f"Author{i}"}],
            )
            for i in range(50)
        ]
        result = compute_j_ec(_make_data(works=works))
        assert result.value < 0.3  # Each author publishes once

    def test_concentrated_authors(self):
        """Few authors dominate -> high concentration."""
        works = []
        # One author publishes 30 papers, 20 unique authors publish 1 each
        for i in range(30):
            works.append(JournalWork(
                work_id=f"W{i}",
                authors=[{"author_id": "A_DOMINANT", "display_name": "Dominant"}],
            ))
        for i in range(20):
            works.append(JournalWork(
                work_id=f"WU{i}",
                authors=[{"author_id": f"A{i}", "display_name": f"Unique{i}"}],
            ))
        result = compute_j_ec(_make_data(works=works))
        assert result.value > 0.2


# ===== J_CB =====


class TestJCB:
    def test_no_citing_journals(self):
        result = compute_j_cb(_make_data())
        assert result.value == 0.0

    def test_only_self_citations(self):
        """All citations from same journal -> no external citations."""
        result = compute_j_cb(_make_data(citing_journals={"S100": 50}))
        assert result.value == 0.0

    def test_single_external_source(self):
        result = compute_j_cb(_make_data(citing_journals={"S200": 50}))
        assert result.value == 1.0  # 100% from one source

    def test_diverse_sources(self):
        result = compute_j_cb(_make_data(citing_journals={
            "S200": 10, "S300": 10, "S400": 10, "S500": 10,
        }))
        assert result.value == 0.25  # Each contributes equally


# ===== J_GROWTH =====


class TestJGrowth:
    def test_insufficient_data(self):
        result = compute_j_growth(_make_data())
        assert result.value == 0.0

    def test_stable_growth(self):
        profile = _make_profile(counts_by_year=[
            {"year": 2018, "works_count": 100, "cited_by_count": 500},
            {"year": 2019, "works_count": 105, "cited_by_count": 520},
            {"year": 2020, "works_count": 110, "cited_by_count": 540},
            {"year": 2021, "works_count": 108, "cited_by_count": 560},
        ])
        result = compute_j_growth(_make_data(profile=profile))
        assert result.value < 0.3  # Stable growth

    def test_sudden_jump(self):
        profile = _make_profile(counts_by_year=[
            {"year": 2018, "works_count": 50},
            {"year": 2019, "works_count": 55},
            {"year": 2020, "works_count": 52},
            {"year": 2021, "works_count": 48},
            {"year": 2022, "works_count": 200},  # sudden 4x jump
        ])
        result = compute_j_growth(_make_data(profile=profile))
        assert result.value > 0.2
