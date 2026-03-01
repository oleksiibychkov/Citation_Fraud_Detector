"""Tests for RLA and GIC indicators."""

from cfd.data.models import AuthorData, AuthorProfile, Citation
from cfd.graph.indicators import compute_gic, compute_rla


def _make_profile():
    return AuthorProfile(
        scopus_id="100", surname="Test", full_name="Test Author",
        h_index=10, publication_count=20, citation_count=100, source_api="test",
    )


def _make_citations(source_ids: list[int | None], self_cit_count: int = 0) -> list[Citation]:
    """Build citations: first self_cit_count are self-citations, rest from source_ids."""
    cits = []
    for i in range(self_cit_count):
        cits.append(Citation(
            source_work_id=f"self-w-{i}", target_work_id=f"self-t-{i}",
            source_author_id=100, target_author_id=100,
            is_self_citation=True, source_api="test",
        ))
    for idx, sid in enumerate(source_ids):
        cits.append(Citation(
            source_work_id=f"w-{idx}", target_work_id=f"t-{idx}",
            source_author_id=sid, target_author_id=100,
            is_self_citation=False, source_api="test",
        ))
    return cits


class TestComputeRLA:
    def test_no_citations(self):
        data = AuthorData(profile=_make_profile(), publications=[], citations=[])
        result = compute_rla(data)
        assert result.indicator_type == "RLA"
        assert result.value == 0.0

    def test_all_self_citations(self):
        cits = _make_citations([], self_cit_count=10)
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_rla(data)
        assert result.value > 0.5  # high self-ref rate + max concentration

    def test_diverse_sources(self):
        cits = _make_citations([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_rla(data)
        assert result.value < 0.3  # diverse sources = low anomaly

    def test_concentrated_sources(self):
        # 8 from same author, 2 from another
        cits = _make_citations([1, 1, 1, 1, 1, 1, 1, 1, 2, 2])
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_rla(data)
        assert result.value > 0.1  # concentrated = higher anomaly

    def test_details_fields(self):
        cits = _make_citations([1, 2, 3], self_cit_count=2)
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_rla(data)
        assert "self_ref_rate" in result.details
        assert "reference_concentration" in result.details
        assert "unique_sources" in result.details
        assert result.details["self_citations"] == 2
        assert result.details["total_citations"] == 5


class TestComputeGIC:
    def test_no_non_self_citations(self):
        cits = _make_citations([], self_cit_count=5)
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_gic(data)
        assert result.indicator_type == "GIC"
        assert result.value == 0.0

    def test_single_source(self):
        cits = _make_citations([1, 1, 1, 1, 1])
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_gic(data)
        # Single source → entropy=0 → GIC=1.0 (maximally suspicious)
        assert result.value == 1.0

    def test_two_equal_sources(self):
        cits = _make_citations([1, 1, 2, 2])
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_gic(data)
        # Equal distribution → max entropy → GIC ≈ 0.0
        assert result.value < 0.1

    def test_highly_skewed(self):
        cits = _make_citations([1, 1, 1, 1, 1, 1, 1, 1, 1, 2])
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_gic(data)
        # Skewed → low entropy → higher GIC
        assert result.value > 0.3

    def test_many_diverse_sources(self):
        cits = _make_citations(list(range(1, 21)))  # 20 unique sources
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_gic(data)
        assert result.value < 0.05  # very diverse

    def test_details_fields(self):
        cits = _make_citations([1, 2, 3, 4])
        data = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        result = compute_gic(data)
        assert "entropy" in result.details
        assert "max_entropy" in result.details
        assert "unique_sources" in result.details
        assert result.details["unique_sources"] == 4
