"""Tests for Coercive Citation Detection (COERCE) indicator."""

from __future__ import annotations

from datetime import date

from cfd.analysis.coercive import detect_coercive_citations
from cfd.data.models import AuthorData, AuthorProfile, Publication


def _profile():
    return AuthorProfile(surname="Test", source_api="openalex")


def test_coerce_no_refs():
    data = AuthorData(profile=_profile(), publications=[], citations=[])
    result = detect_coercive_citations(data)
    assert result.indicator_type == "COERCE"
    assert result.value == 0.0
    assert result.details["status"] == "no_references"


def test_coerce_no_concentration():
    """Refs spread across many journals → no coercive signal."""
    pubs = [
        Publication(
            work_id="W1", journal="J1",
            references_list=["W2", "W3", "W4", "W5"],
            publication_date=date(2024, 1, 1),
            source_api="openalex",
        ),
        Publication(work_id="W2", journal="J2", publication_date=date(2023, 1, 1), source_api="openalex"),
        Publication(work_id="W3", journal="J3", publication_date=date(2022, 1, 1), source_api="openalex"),
        Publication(work_id="W4", journal="J4", publication_date=date(2021, 1, 1), source_api="openalex"),
        Publication(work_id="W5", journal="J5", publication_date=date(2020, 1, 1), source_api="openalex"),
    ]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = detect_coercive_citations(data)
    # 1 ref per journal out of 4 = 25% concentration → gradient signal = max(0, (0.25-0.20)/0.40) = 0.125
    assert result.details["signal_concentration"] < 0.2
    assert result.value < 0.15


def test_coerce_high_concentration():
    """All refs to one journal → concentration signal fires strongly."""
    pubs = [
        Publication(
            work_id="W1", journal="BadJournal",
            references_list=["W2", "W3"],
            publication_date=date(2024, 1, 1),
            source_api="openalex",
        ),
        Publication(work_id="W2", journal="BadJournal", publication_date=date(2023, 6, 1), source_api="openalex"),
        Publication(work_id="W3", journal="BadJournal", publication_date=date(2023, 1, 1), source_api="openalex"),
    ]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = detect_coercive_citations(data)
    # 100% concentration → gradient = (1.0-0.20)/0.40 = 2.0 → capped to 1.0
    assert result.details["signal_concentration"] == 1.0
    assert result.value > 0


def test_coerce_recent_bias():
    """Same-journal refs all from recent years → recent bias signal fires."""
    pubs = [
        Publication(
            work_id="W1", journal="JX",
            references_list=["W2", "W3"],
            publication_date=date(2024, 6, 1),
            source_api="openalex",
        ),
        Publication(work_id="W2", journal="JX", publication_date=date(2023, 1, 1), source_api="openalex"),
        Publication(work_id="W3", journal="JX", publication_date=date(2024, 1, 1), source_api="openalex"),
    ]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = detect_coercive_citations(data)
    # 100% recent → gradient = (1.0-0.50)/0.30 = 1.67 → capped to 1.0
    assert result.details["signal_recent_bias"] == 1.0


def test_coerce_all_signals():
    """When all signals fire strongly → high value."""
    pubs = [
        # Early: same-journal ref from far past
        Publication(
            work_id="E1", journal="JX",
            references_list=["E2", "E3", "E4", "E5"],
            publication_date=date(2020, 1, 1),
            source_api="openalex",
        ),
        Publication(work_id="E2", journal="JX", publication_date=date(2015, 1, 1), source_api="openalex"),
        Publication(work_id="E3", journal="Other", publication_date=date(2019, 1, 1), source_api="openalex"),
        Publication(work_id="E4", journal="Other2", publication_date=date(2018, 1, 1), source_api="openalex"),
        Publication(work_id="E5", journal="Other3", publication_date=date(2018, 1, 1), source_api="openalex"),
        # Late: all same-journal refs recent
        Publication(
            work_id="L1", journal="JX",
            references_list=["L2", "L3"],
            publication_date=date(2024, 6, 1),
            source_api="openalex",
        ),
        Publication(work_id="L2", journal="JX", publication_date=date(2024, 1, 1), source_api="openalex"),
        Publication(work_id="L3", journal="JX", publication_date=date(2023, 1, 1), source_api="openalex"),
    ]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = detect_coercive_citations(data)
    # Concentration, recent bias, and trend should all contribute
    assert result.value > 0.5
    assert result.details["signal_concentration"] > 0
    assert result.details["signal_recent_bias"] > 0


def test_coerce_details_populated():
    pubs = [
        Publication(
            work_id="W1", journal="J1",
            references_list=["W2"],
            publication_date=date(2024, 1, 1),
            source_api="openalex",
        ),
        Publication(work_id="W2", journal="J1", publication_date=date(2023, 6, 1), source_api="openalex"),
    ]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = detect_coercive_citations(data)
    assert "total_refs" in result.details
    assert "concentration" in result.details
    assert "signal_concentration" in result.details
    assert "signal_recent_bias" in result.details
