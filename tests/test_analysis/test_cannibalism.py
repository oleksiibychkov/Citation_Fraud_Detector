"""Tests for Citation Cannibalism (CC) indicator."""

from datetime import date

from cfd.analysis.cannibalism import _per_paper_cc, compute_cc
from cfd.data.models import AuthorData, AuthorProfile, Publication


def _make_profile(**kw):
    defaults = {"surname": "Test", "source_api": "openalex"}
    defaults.update(kw)
    return AuthorProfile(**defaults)


def _make_pub(work_id, refs=None, **kw):
    return Publication(
        work_id=work_id,
        title=f"Paper {work_id}",
        publication_date=date(2023, 1, 1),
        references_list=refs or [],
        source_api="openalex",
        **kw,
    )


class TestComputeCC:
    def test_no_publications(self):
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        result = compute_cc(ad)
        assert result.indicator_type == "CC"
        assert result.value == 0.0
        assert result.details["status"] == "no_references"

    def test_no_references(self):
        pubs = [_make_pub("W1"), _make_pub("W2")]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_cc(ad)
        assert result.value == 0.0

    def test_all_self_references(self):
        pubs = [
            _make_pub("W1", refs=["W2", "W3"]),
            _make_pub("W2", refs=["W1", "W3"]),
            _make_pub("W3", refs=["W1", "W2"]),
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_cc(ad)
        assert result.value == 1.0

    def test_no_self_references(self):
        pubs = [
            _make_pub("W1", refs=["EXT1", "EXT2"]),
            _make_pub("W2", refs=["EXT3", "EXT4"]),
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_cc(ad)
        assert result.value == 0.0

    def test_mixed_references(self):
        pubs = [
            _make_pub("W1", refs=["W2", "EXT1", "EXT2", "EXT3"]),  # CC = 0.25
            _make_pub("W2", refs=["W1", "W1", "W1", "EXT1"]),  # CC = 0.75 (flagged)
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_cc(ad, per_paper_threshold=0.50)
        assert result.value == 0.5  # 1 of 2 flagged

    def test_custom_threshold(self):
        pubs = [_make_pub("W1", refs=["W2", "EXT1"])]  # CC = 0.5
        ad = AuthorData(profile=_make_profile(), publications=[pubs[0], _make_pub("W2")], citations=[])
        result_low = compute_cc(ad, per_paper_threshold=0.3)
        result_high = compute_cc(ad, per_paper_threshold=0.6)
        assert result_low.value >= result_high.value

    def test_details_fields(self):
        pubs = [_make_pub("W1", refs=["W2", "EXT1"]), _make_pub("W2", refs=["EXT1"])]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_cc(ad)
        assert "mean_cc" in result.details
        assert "max_cc" in result.details
        assert "flagged_count" in result.details
        assert "total_evaluated" in result.details

    def test_value_normalized(self):
        pubs = [_make_pub(f"W{i}", refs=[f"W{j}" for j in range(10)]) for i in range(10)]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_cc(ad)
        assert 0.0 <= result.value <= 1.0


class TestPerPaperCC:
    def test_empty_references(self):
        pub = _make_pub("W1", refs=[])
        assert _per_paper_cc(pub, {"W1"}) is None

    def test_all_self(self):
        pub = _make_pub("W1", refs=["W2", "W3"])
        assert _per_paper_cc(pub, {"W1", "W2", "W3"}) == 1.0

    def test_no_self(self):
        pub = _make_pub("W1", refs=["EXT1", "EXT2"])
        assert _per_paper_cc(pub, {"W1"}) == 0.0

    def test_partial_self(self):
        pub = _make_pub("W1", refs=["W2", "EXT1"])
        cc = _per_paper_cc(pub, {"W1", "W2"})
        assert abs(cc - 0.5) < 1e-10
