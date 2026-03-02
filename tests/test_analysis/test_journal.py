"""Tests for Journal Self-Citation Rate (JSCR) indicator."""

from __future__ import annotations

from cfd.analysis.journal import compute_jscr
from cfd.data.models import AuthorData, AuthorProfile, Publication


def _profile():
    return AuthorProfile(surname="Test", source_api="openalex")


def test_jscr_no_publications():
    data = AuthorData(profile=_profile(), publications=[], citations=[])
    result = compute_jscr(data)
    assert result.indicator_type == "JSCR"
    assert result.value == 0.0
    assert result.details["status"] == "no_references"


def test_jscr_no_references():
    pubs = [Publication(work_id="W1", journal="Nature", source_api="openalex")]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = compute_jscr(data)
    assert result.value == 0.0


def test_jscr_all_same_journal():
    """All references point to papers in the same journal → JSCR=1.0."""
    pubs = [
        Publication(work_id="W1", journal="Nature", references_list=["W2", "W3"], source_api="openalex"),
        Publication(work_id="W2", journal="Nature", source_api="openalex"),
        Publication(work_id="W3", journal="Nature", source_api="openalex"),
    ]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = compute_jscr(data)
    assert result.value == 1.0
    assert result.details["same_journal_refs"] == 2
    assert result.details["total_refs"] == 2


def test_jscr_no_same_journal():
    """All references point to papers in different journals → JSCR=0.0."""
    pubs = [
        Publication(work_id="W1", journal="Nature", references_list=["W2"], source_api="openalex"),
        Publication(work_id="W2", journal="Science", source_api="openalex"),
    ]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = compute_jscr(data)
    assert result.value == 0.0


def test_jscr_mixed():
    """Mixed: 1 out of 3 refs in same journal → JSCR≈0.3333."""
    pubs = [
        Publication(work_id="W1", journal="Nature", references_list=["W2", "W3", "W4"], source_api="openalex"),
        Publication(work_id="W2", journal="Nature", source_api="openalex"),
        Publication(work_id="W3", journal="Science", source_api="openalex"),
        Publication(work_id="W4", journal="Lancet", source_api="openalex"),
    ]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = compute_jscr(data)
    assert abs(result.value - 0.3333) < 0.01


def test_jscr_external_refs_ignored():
    """Refs to unknown works (not in author's publications) are counted as total but not same-journal."""
    pubs = [
        Publication(work_id="W1", journal="Nature", references_list=["W2", "UNKNOWN"], source_api="openalex"),
        Publication(work_id="W2", journal="Nature", source_api="openalex"),
    ]
    data = AuthorData(profile=_profile(), publications=pubs, citations=[])
    result = compute_jscr(data)
    # 1 same-journal ref out of 2 total refs
    assert result.value == 0.5
