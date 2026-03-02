"""Tests for Cross-Platform Consistency (CPC) indicator."""

from unittest.mock import MagicMock

from cfd.analysis.cross_platform import (
    _best_title_match,
    _compute_metric_divergences,
    compute_cpc,
    fuzzy_publication_match,
)
from cfd.data.models import AuthorData, AuthorProfile, Publication


def _make_profile(**kw):
    defaults = {"surname": "Test", "source_api": "openalex"}
    defaults.update(kw)
    return AuthorProfile(**defaults)


class TestComputeCPC:
    def test_no_secondary_strategy(self):
        ad = AuthorData(profile=_make_profile(h_index=10, publication_count=20, citation_count=200))
        result = compute_cpc(ad)
        assert result.indicator_type == "CPC"
        assert result.value == 0.0
        assert result.details["status"] == "single_source"

    def test_secondary_api_fails(self):
        strategy = MagicMock()
        strategy.fetch_author.side_effect = Exception("API error")

        ad = AuthorData(profile=_make_profile(h_index=10, publication_count=20, citation_count=200))
        result = compute_cpc(ad, secondary_strategy=strategy)
        assert result.value == 0.0
        assert result.details["status"] == "secondary_api_failed"

    def test_identical_profiles(self):
        secondary_profile = _make_profile(
            source_api="scopus", h_index=10, publication_count=20, citation_count=200,
        )
        strategy = MagicMock()
        strategy.fetch_author.return_value = secondary_profile

        ad = AuthorData(profile=_make_profile(h_index=10, publication_count=20, citation_count=200))
        result = compute_cpc(ad, secondary_strategy=strategy)
        assert result.value == 0.0

    def test_divergent_metrics(self):
        secondary_profile = _make_profile(
            source_api="scopus", h_index=5, publication_count=10, citation_count=100,
        )
        strategy = MagicMock()
        strategy.fetch_author.return_value = secondary_profile

        ad = AuthorData(profile=_make_profile(h_index=20, publication_count=50, citation_count=500))
        result = compute_cpc(ad, secondary_strategy=strategy, divergence_threshold=0.20)
        assert result.value > 0.0

    def test_all_metrics_divergent(self):
        secondary_profile = _make_profile(
            source_api="scopus", h_index=1, publication_count=1, citation_count=1,
        )
        strategy = MagicMock()
        strategy.fetch_author.return_value = secondary_profile

        ad = AuthorData(profile=_make_profile(h_index=100, publication_count=100, citation_count=10000))
        result = compute_cpc(ad, secondary_strategy=strategy, divergence_threshold=0.10)
        assert result.value == 1.0

    def test_details_fields(self):
        secondary_profile = _make_profile(source_api="scopus", h_index=10, publication_count=20, citation_count=200)
        strategy = MagicMock()
        strategy.fetch_author.return_value = secondary_profile

        ad = AuthorData(profile=_make_profile(h_index=10, publication_count=20, citation_count=200))
        result = compute_cpc(ad, secondary_strategy=strategy)
        assert "divergences" in result.details
        assert "primary_source" in result.details
        assert "secondary_source" in result.details

    def test_value_normalized(self):
        secondary_profile = _make_profile(source_api="scopus", h_index=1, publication_count=1, citation_count=1)
        strategy = MagicMock()
        strategy.fetch_author.return_value = secondary_profile

        ad = AuthorData(profile=_make_profile(h_index=100, publication_count=100, citation_count=10000))
        result = compute_cpc(ad, secondary_strategy=strategy)
        assert 0.0 <= result.value <= 1.0


class TestComputeMetricDivergences:
    def test_identical(self):
        p = _make_profile(h_index=10, publication_count=20, citation_count=200)
        s = _make_profile(h_index=10, publication_count=20, citation_count=200)
        divs = _compute_metric_divergences(p, s)
        for d in divs.values():
            assert d["divergence"] == 0.0

    def test_none_values(self):
        p = _make_profile(h_index=None, publication_count=20, citation_count=200)
        s = _make_profile(h_index=10, publication_count=20, citation_count=200)
        divs = _compute_metric_divergences(p, s)
        assert divs["h_index"]["divergence"] is None


class TestFuzzyPublicationMatch:
    def test_doi_match(self):
        primary = [Publication(work_id="W1", doi="10.1234/abc", source_api="openalex")]
        secondary = [Publication(work_id="S1", doi="10.1234/abc", source_api="scopus")]
        result = fuzzy_publication_match(primary, secondary)
        assert result["matched_by_doi"] == 1

    def test_title_match(self):
        primary = [Publication(work_id="W1", title="Study of machine learning", source_api="openalex")]
        secondary = [Publication(work_id="S1", title="Study of machine learning", source_api="scopus")]
        result = fuzzy_publication_match(primary, secondary)
        assert result["matched_by_doi"] + result["matched_by_title"] >= 1

    def test_no_match(self):
        primary = [Publication(work_id="W1", title="Alpha", source_api="openalex")]
        secondary = [Publication(work_id="S1", title="Completely different", source_api="scopus")]
        result = fuzzy_publication_match(primary, secondary)
        assert result["unmatched"] == 1


class TestBestTitleMatch:
    def test_exact(self):
        assert _best_title_match("hello world", {"hello world"}) == 1.0

    def test_no_match(self):
        assert _best_title_match("abc", {"xyz"}) < 0.5

    def test_empty_set(self):
        assert _best_title_match("hello", set()) == 0.0
