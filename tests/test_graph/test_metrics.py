"""Tests for graph-based indicator computations."""

from datetime import date

import networkx as nx
import pytest

from cfd.data.models import AuthorData, AuthorProfile, Citation, Publication
from cfd.graph.metrics import (
    compute_cb,
    compute_degree_centrality,
    compute_hta,
    compute_mcr,
    compute_mcr_from_author_data,
    compute_scr,
    compute_ta,
)


@pytest.fixture
def author_with_self_citations():
    """Author data with known self-citation ratio."""
    profile = AuthorProfile(
        scopus_id="100", surname="Test", full_name="Test Author",
        h_index=10, publication_count=20, citation_count=100, source_api="test",
    )
    citations = []
    # 3 self-citations
    for i in range(3):
        citations.append(Citation(
            source_work_id=f"W{i}", target_work_id=f"T{i}",
            source_author_id="1", target_author_id="1",
            citation_date=date(2022, 1, 1), is_self_citation=True, source_api="test",
        ))
    # 7 external citations
    for i in range(7):
        citations.append(Citation(
            source_work_id=f"EXT{i}", target_work_id=f"T{i}",
            source_author_id=str(i + 10), target_author_id="1",
            citation_date=date(2022, 1, 1), is_self_citation=False, source_api="test",
        ))
    return AuthorData(profile=profile, publications=[], citations=citations)


class TestComputeSCR:
    def test_known_ratio(self, author_with_self_citations):
        result = compute_scr(author_with_self_citations)
        assert result.indicator_type == "SCR"
        assert result.value == pytest.approx(0.3)
        assert result.details["self_citations"] == 3
        assert result.details["total_citations"] == 10

    def test_no_citations(self):
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[], citations=[],
        )
        result = compute_scr(data)
        assert result.value == 0.0

    def test_all_self_citations(self):
        citations = [
            Citation(
                source_work_id=f"W{i}", target_work_id=f"T{i}",
                source_author_id="1", target_author_id="1",
                is_self_citation=True, source_api="test",
            )
            for i in range(5)
        ]
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[], citations=citations,
        )
        result = compute_scr(data)
        assert result.value == pytest.approx(1.0)


class TestComputeMCR:
    def test_symmetric_citations(self):
        cit_a = [
            Citation(source_work_id="WA1", target_work_id="WB1",
                     source_author_id="1", target_author_id="2", source_api="test"),
            Citation(source_work_id="WA2", target_work_id="WB2",
                     source_author_id="1", target_author_id="2", source_api="test"),
        ]
        cit_b = [
            Citation(source_work_id="WB3", target_work_id="WA3",
                     source_author_id="2", target_author_id="1", source_api="test"),
        ]
        result = compute_mcr(cit_a, cit_b, 1, 2)
        # a cites b: 2, b cites a: 1, mutual = min(2,1)=1, total=3
        # MCR = 2*1/3 = 0.6667
        assert result.indicator_type == "MCR"
        assert result.value == pytest.approx(2 / 3)

    def test_no_mutual(self):
        cit_a = [
            Citation(source_work_id="WA1", target_work_id="WB1",
                     source_author_id="1", target_author_id="2", source_api="test"),
        ]
        cit_b = []
        result = compute_mcr(cit_a, cit_b, 1, 2)
        # mutual = min(1, 0) = 0
        assert result.value == 0.0

    def test_empty_citations(self):
        result = compute_mcr([], [], 1, 2)
        assert result.value == 0.0


class TestComputeMCRFromAuthorData:
    def test_with_citing_authors(self, sample_author_data):
        result = compute_mcr_from_author_data(sample_author_data)
        assert result.indicator_type == "MCR"
        assert result.value >= 0.0

    def test_no_external_citations(self):
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[],
            citations=[
                Citation(source_work_id="W1", target_work_id="W2",
                         source_author_id="1", target_author_id="1",
                         is_self_citation=True, source_api="test"),
            ],
        )
        result = compute_mcr_from_author_data(data)
        assert result.value == 0.0
        assert result.details.get("status") == "no_citing_authors"


class TestComputeCB:
    def test_concentrated_citations(self):
        citations = []
        # 8 citations from author 10
        for i in range(8):
            citations.append(Citation(
                source_work_id=f"EXT{i}", target_work_id=f"W{i}",
                source_author_id="10", target_author_id="1",
                is_self_citation=False, source_api="test",
            ))
        # 2 citations from author 11
        for i in range(2):
            citations.append(Citation(
                source_work_id=f"EXT2_{i}", target_work_id=f"W{i}",
                source_author_id="11", target_author_id="1",
                is_self_citation=False, source_api="test",
            ))
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[], citations=citations,
        )
        result = compute_cb(data)
        assert result.indicator_type == "CB"
        assert result.value == pytest.approx(0.8)
        assert result.details["max_source_count"] == 8
        assert result.details["total_incoming"] == 10

    def test_no_external_citations(self):
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[],
            citations=[
                Citation(source_work_id="W1", target_work_id="W2",
                         source_author_id="1", target_author_id="1",
                         is_self_citation=True, source_api="test"),
            ],
        )
        result = compute_cb(data)
        assert result.value == 0.0


class TestComputeTA:
    def test_with_spike(self):
        citations = []
        # Normal years: ~5 citations each
        for year in [2018, 2019, 2020, 2021]:
            for i in range(5):
                citations.append(Citation(
                    source_work_id=f"E_{year}_{i}", target_work_id=f"W{i}",
                    source_author_id="10", target_author_id="1",
                    citation_date=date(year, 6, 1),
                    is_self_citation=False, source_api="test",
                ))
        # Spike year: 50 citations
        for i in range(50):
            citations.append(Citation(
                source_work_id=f"E_2022_{i}", target_work_id=f"W{i % 5}",
                source_author_id=str(10 + i), target_author_id="1",
                citation_date=date(2022, 6, 1),
                is_self_citation=False, source_api="test",
            ))
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[], citations=citations,
        )
        result = compute_ta(data)
        assert result.indicator_type == "TA"
        assert result.value > 0
        assert result.details["spike_year"] == 2022

    def test_no_timestamps(self):
        citations = [
            Citation(source_work_id="E1", target_work_id="W1",
                     source_author_id="10", target_author_id="1",
                     is_self_citation=False, source_api="test"),
        ]
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[], citations=citations,
        )
        result = compute_ta(data)
        assert result.value == 0.0
        assert result.details.get("status") == "N/A"

    def test_insufficient_years(self):
        citations = [
            Citation(source_work_id="E1", target_work_id="W1",
                     source_author_id="10", target_author_id="1",
                     citation_date=date(2022, 1, 1),
                     is_self_citation=False, source_api="test"),
            Citation(source_work_id="E2", target_work_id="W2",
                     source_author_id="11", target_author_id="1",
                     citation_date=date(2022, 6, 1),
                     is_self_citation=False, source_api="test"),
        ]
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[], citations=citations,
        )
        result = compute_ta(data)
        assert result.value == 0.0


class TestComputeHTA:
    def test_with_growth_data(self):
        pubs = [
            Publication(
                work_id="W1", title="P1", source_api="test",
                raw_data={"counts_by_year": [
                    {"year": 2018, "cited_by_count": 10},
                    {"year": 2019, "cited_by_count": 12},
                    {"year": 2020, "cited_by_count": 11},
                    {"year": 2021, "cited_by_count": 50},  # anomalous spike
                ]},
            ),
        ]
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=pubs, citations=[],
        )
        result = compute_hta(data)
        assert result.indicator_type == "HTA"
        assert result.value >= 0.0

    def test_insufficient_data(self):
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[], citations=[],
        )
        result = compute_hta(data)
        assert result.value == 0.0
        assert result.details.get("status") == "N/A"


class TestDegreeCentrality:
    def test_known_graph(self):
        g = nx.DiGraph()
        g.add_edges_from([("A", "B"), ("A", "C"), ("D", "A")])
        in_c, out_c = compute_degree_centrality(g, "A")
        # A has in_degree=1 (from D), out_degree=2 (to B, C), n=4
        assert in_c.value == pytest.approx(1 / 3)
        assert out_c.value == pytest.approx(2 / 3)

    def test_missing_node(self):
        g = nx.DiGraph()
        g.add_edge("A", "B")
        in_c, out_c = compute_degree_centrality(g, "Z")
        assert in_c.value == 0.0
        assert out_c.value == 0.0
