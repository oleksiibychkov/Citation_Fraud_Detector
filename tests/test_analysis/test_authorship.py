"""Tests for Authorship Network Anomaly (ANA) indicator."""

from datetime import date

from cfd.analysis.authorship import compute_ana
from cfd.data.models import AuthorData, AuthorProfile, Publication


def _make_profile(**kw):
    defaults = {"surname": "Test", "source_api": "openalex", "openalex_id": "A1"}
    defaults.update(kw)
    return AuthorProfile(**defaults)


def _make_pub(work_id, co_authors=None, **kw):
    return Publication(
        work_id=work_id,
        title=f"Paper {work_id}",
        publication_date=date(2023, 1, 1),
        co_authors=co_authors or [],
        source_api="openalex",
        **kw,
    )


def _ca(author_id, name="Coauthor", position="middle"):
    return {"author_id": author_id, "display_name": name, "position": position}


class TestComputeANA:
    def test_no_publications(self):
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        result = compute_ana(ad)
        assert result.indicator_type == "ANA"
        assert result.value == 0.0

    def test_no_coauthors(self):
        pubs = [_make_pub("W1"), _make_pub("W2")]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ana(ad)
        assert result.value == 0.0

    def test_all_unique_coauthors_high_ana(self):
        """Every paper has different co-authors → high single-paper ratio."""
        pubs = [
            _make_pub("W1", co_authors=[_ca("A1", position="first"), _ca("C1")]),
            _make_pub("W2", co_authors=[_ca("A1", position="first"), _ca("C2")]),
            _make_pub("W3", co_authors=[_ca("A1", position="first"), _ca("C3")]),
        ]
        ad = AuthorData(profile=_make_profile(publication_count=15), publications=pubs, citations=[])
        result = compute_ana(ad)
        # All co-authors are unique → high single_paper_coauthor_ratio
        assert result.details["single_paper_coauthor_ratio"] == 1.0

    def test_repeat_collaborators_lower_ana(self):
        """Same co-author across papers → lower ANA."""
        pubs = [
            _make_pub("W1", co_authors=[_ca("A1", position="first"), _ca("C1")]),
            _make_pub("W2", co_authors=[_ca("A1", position="first"), _ca("C1")]),
            _make_pub("W3", co_authors=[_ca("A1", position="first"), _ca("C1")]),
        ]
        ad = AuthorData(profile=_make_profile(publication_count=15), publications=pubs, citations=[])
        result = compute_ana(ad)
        assert result.details["single_paper_coauthor_ratio"] == 0.0

    def test_always_middle_position_suspicious(self):
        """Author always in middle position with many pubs."""
        pubs = [
            _make_pub(f"W{i}", co_authors=[
                _ca("F1", position="first"),
                _ca("A1", position="middle"),
                _ca("L1", position="last"),
            ])
            for i in range(5)
        ]
        ad = AuthorData(profile=_make_profile(publication_count=15), publications=pubs, citations=[])
        result = compute_ana(ad)
        assert result.details["position_anomaly_score"] > 0.0

    def test_first_last_position_not_suspicious(self):
        """Author usually first/last → low position anomaly."""
        pubs = [
            _make_pub(f"W{i}", co_authors=[
                _ca("A1", position="first"),
                _ca("C1", position="last"),
            ])
            for i in range(5)
        ]
        ad = AuthorData(profile=_make_profile(publication_count=15), publications=pubs, citations=[])
        result = compute_ana(ad)
        assert result.details["position_anomaly_score"] == 0.0

    def test_details_present(self):
        pubs = [_make_pub("W1", co_authors=[_ca("A1"), _ca("C1")])]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ana(ad)
        assert "unique_coauthors" in result.details
        assert "repeat_collaboration_rate" in result.details
        assert "position_distribution" in result.details

    def test_value_normalized(self):
        pubs = [
            _make_pub(f"W{i}", co_authors=[_ca(f"C{i}")])
            for i in range(10)
        ]
        ad = AuthorData(profile=_make_profile(publication_count=20), publications=pubs, citations=[])
        result = compute_ana(ad)
        assert 0.0 <= result.value <= 1.0

    def test_fallback_to_raw_data(self):
        """When co_authors is empty, fallback to raw_data."""
        raw = {"authorships": [
            {"author": {"id": "https://openalex.org/A1", "display_name": "Me"}, "author_position": "first"},
            {"author": {"id": "https://openalex.org/C1", "display_name": "Other"}, "author_position": "last"},
        ]}
        pubs = [_make_pub("W1", raw_data=raw)]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ana(ad)
        assert result.details["total_papers_with_coauthors"] >= 1

    def test_few_publications_no_position_penalty(self):
        """Author with < 10 pubs shouldn't get position anomaly."""
        pubs = [
            _make_pub("W1", co_authors=[_ca("F1", position="first"), _ca("A1", position="middle")]),
        ]
        ad = AuthorData(profile=_make_profile(publication_count=5), publications=pubs, citations=[])
        result = compute_ana(ad)
        assert result.details["position_anomaly_score"] == 0.0
