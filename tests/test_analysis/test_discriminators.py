"""Tests for discriminative indicators (CDF, HIA, CCL, LRHC)."""

from datetime import date

from cfd.analysis.baselines import DisciplineBaseline
from cfd.analysis.discriminators import compute_ccl, compute_cdf, compute_hia, compute_lrhc
from cfd.data.models import AuthorData, AuthorProfile, Publication


def _profile(**kw):
    defaults = {"surname": "Test", "source_api": "openalex"}
    defaults.update(kw)
    return AuthorProfile(**defaults)


def _pub(work_id, citation_count=0, references_list=None, raw_data=None, **kw):
    return Publication(
        work_id=work_id,
        citation_count=citation_count,
        references_list=references_list or [],
        raw_data=raw_data,
        source_api="openalex",
        publication_date=kw.pop("publication_date", date(2020, 1, 1)),
        **kw,
    )


def _baseline():
    return DisciplineBaseline(
        discipline="Computer Science",
        avg_scr=0.15,
        std_scr=0.05,
        avg_citations_per_paper=8.5,
        avg_h_index_growth_rate=1.2,
        citation_half_life_years=6.0,
        avg_papers_per_year=3.0,
    )


# ---- CDF Tests ----

class TestComputeCDF:
    def test_insufficient_data(self):
        pubs = [_pub(f"W{i}", citation_count=5) for i in range(3)]
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_cdf(ad)
        assert result.indicator_type == "CDF"
        assert result.value == 0.0

    def test_flat_distribution_high_score(self):
        """All papers with exactly same citations → Gini≈0 → high score."""
        pubs = [_pub(f"W{i}", citation_count=25) for i in range(20)]
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_cdf(ad)
        assert result.value > 0.7

    def test_natural_distribution_low_score(self):
        """Power-law-like: one high, rest low → normal Gini → low score."""
        counts = [100, 50, 20, 10, 5, 3, 2, 1, 1, 1]
        pubs = [_pub(f"W{i}", citation_count=c) for i, c in enumerate(counts)]
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_cdf(ad)
        assert result.value < 0.3

    def test_details_populated(self):
        pubs = [_pub(f"W{i}", citation_count=10 + i) for i in range(10)]
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_cdf(ad)
        assert "gini_coefficient" in result.details
        assert "top_n_cv" in result.details


# ---- HIA Tests ----

class TestComputeHIA:
    def test_insufficient_data(self):
        ad = AuthorData(profile=_profile(h_index=2, publication_count=3, citation_count=10), publications=[], citations=[])
        result = compute_hia(ad, _baseline())
        assert result.value == 0.0

    def test_anomalous_h_high_score(self):
        """h=18 with 63 works and 550 citations → anomalous."""
        pubs = [_pub(f"W{i}", citation_count=20) for i in range(22)] + [
            _pub(f"W{i}", citation_count=3) for i in range(22, 63)
        ]
        ad = AuthorData(
            profile=_profile(h_index=18, publication_count=63, citation_count=550),
            publications=pubs, citations=[],
        )
        result = compute_hia(ad, _baseline())
        assert result.value > 0.4

    def test_normal_h_low_score(self):
        """h=7 with 72 works and 215 citations → normal."""
        pubs = [_pub(f"W{i}", citation_count=15) for i in range(4)] + [
            _pub(f"W{i}", citation_count=2) for i in range(4, 72)
        ]
        ad = AuthorData(
            profile=_profile(h_index=7, publication_count=72, citation_count=215),
            publications=pubs, citations=[],
        )
        result = compute_hia(ad, _baseline())
        assert result.value < 0.3

    def test_details_populated(self):
        pubs = [_pub(f"W{i}", citation_count=5) for i in range(10)]
        ad = AuthorData(
            profile=_profile(h_index=5, publication_count=10, citation_count=50),
            publications=pubs, citations=[],
        )
        result = compute_hia(ad, _baseline())
        assert "h_expected" in result.details
        assert "h_works_ratio" in result.details


# ---- CCL Tests ----

class TestComputeCCL:
    def _make_yearly_data(self, yearly_dict):
        """Create publications with counts_by_year raw data."""
        pubs = []
        for year, (works, cites) in yearly_dict.items():
            for i in range(works):
                pubs.append(_pub(
                    f"W{year}_{i}",
                    publication_date=date(year, 6, 1),
                    raw_data={"counts_by_year": [{"year": year, "cited_by_count": cites // max(works, 1)}]},
                ))
        return pubs

    def test_insufficient_data(self):
        ad = AuthorData(profile=_profile(), publications=[], citations=[])
        result = compute_ccl(ad)
        assert result.value == 0.0

    def test_collapse_high_score(self):
        """203→85→9→0 pattern → high collapse score."""
        pubs = []
        yearly = {2018: 3, 2019: 6, 2020: 14, 2021: 7, 2022: 9, 2023: 1}
        cit_yearly = {2018: 1, 2019: 104, 2020: 203, 2021: 85, 2022: 9, 2023: 0}
        for year, works in yearly.items():
            for i in range(works):
                pubs.append(_pub(
                    f"W{year}_{i}",
                    publication_date=date(year, 6, 1),
                    raw_data={"counts_by_year": [{"year": year, "cited_by_count": cit_yearly[year] // max(works, 1)}]},
                ))
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_ccl(ad)
        assert result.value > 0.3

    def test_stable_low_score(self):
        """Gradual, steady citations → low collapse score."""
        pubs = []
        for year in range(2018, 2024):
            for i in range(5):
                pubs.append(_pub(
                    f"W{year}_{i}",
                    publication_date=date(year, 6, 1),
                    raw_data={"counts_by_year": [{"year": year, "cited_by_count": 6}]},
                ))
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_ccl(ad)
        assert result.value < 0.3

    def test_low_peak_ignored(self):
        """Peak < 20 → returns 0."""
        pubs = [_pub("W1", publication_date=date(2020, 1, 1),
                      raw_data={"counts_by_year": [{"year": 2020, "cited_by_count": 10}]})]
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_ccl(ad)
        assert result.value == 0.0


# ---- LRHC Tests ----

class TestComputeLRHC:
    def test_no_cited_papers(self):
        pubs = [_pub("W1", citation_count=0)]
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_lrhc(ad)
        assert result.value == 0.0

    def test_low_refs_high_cites_high_score(self):
        """Papers with 3 refs and 26 cites → anomalous."""
        pubs = [
            _pub("W1", citation_count=26, references_list=["R1", "R2", "R3"]),
            _pub("W2", citation_count=27, references_list=["R1", "R2"]),
            _pub("W3", citation_count=25, references_list=["R1"]),
        ]
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_lrhc(ad)
        assert result.value > 0.5

    def test_normal_refs_low_score(self):
        """Papers with 20+ refs and citations → normal."""
        pubs = [
            _pub("W1", citation_count=30, references_list=[f"R{i}" for i in range(25)]),
            _pub("W2", citation_count=20, references_list=[f"R{i}" for i in range(20)]),
            _pub("W3", citation_count=10, references_list=[f"R{i}" for i in range(15)]),
        ]
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_lrhc(ad)
        assert result.value == 0.0

    def test_details_populated(self):
        pubs = [_pub("W1", citation_count=10, references_list=["R1"])]
        ad = AuthorData(profile=_profile(), publications=pubs, citations=[])
        result = compute_lrhc(ad)
        assert "anomalous_papers" in result.details
        assert "total_cited_papers" in result.details
