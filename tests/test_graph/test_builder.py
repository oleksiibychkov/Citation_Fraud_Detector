"""Tests for graph construction from citation data."""

from datetime import date

from cfd.data.models import AuthorData, AuthorProfile, Citation, Publication
from cfd.graph.builder import build_author_graph, build_citation_graph


class TestBuildCitationGraph:
    def test_basic_graph(self, sample_author_data):
        g = build_citation_graph(sample_author_data)
        assert len(g.nodes) > 0
        assert len(g.edges) > 0

    def test_publications_as_nodes(self, sample_publications):
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=sample_publications,
            citations=[],
        )
        g = build_citation_graph(data)
        for pub in sample_publications:
            assert pub.work_id in g.nodes
            assert g.nodes[pub.work_id]["type"] == "publication"

    def test_external_nodes_added(self):
        citations = [
            Citation(
                source_work_id="EXT1", target_work_id="W1",
                source_author_id="10", target_author_id="1",
                source_api="test",
            ),
        ]
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[
                Publication(work_id="W1", title="P1", source_api="test"),
            ],
            citations=citations,
        )
        g = build_citation_graph(data)
        assert "EXT1" in g.nodes
        assert g.nodes["EXT1"]["type"] == "external"

    def test_edge_attributes(self):
        citations = [
            Citation(
                source_work_id="W1", target_work_id="W2",
                source_author_id="1", target_author_id="1",
                citation_date=date(2022, 6, 1),
                is_self_citation=True, source_api="test",
            ),
        ]
        pubs = [
            Publication(work_id="W1", title="P1", source_api="test"),
            Publication(work_id="W2", title="P2", source_api="test"),
        ]
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=pubs, citations=citations,
        )
        g = build_citation_graph(data)
        edge_data = g.edges["W1", "W2"]
        assert edge_data["is_self_citation"] is True
        assert edge_data["citation_date"] == "2022-06-01"

    def test_empty_data(self):
        data = AuthorData(
            profile=AuthorProfile(scopus_id="1", surname="X", source_api="test"),
            publications=[], citations=[],
        )
        g = build_citation_graph(data)
        assert len(g.nodes) == 0
        assert len(g.edges) == 0


class TestBuildAuthorGraph:
    def test_basic_graph(self):
        citations = [
            Citation(source_work_id="W1", target_work_id="W2",
                     source_author_id="1", target_author_id="2", source_api="test"),
            Citation(source_work_id="W3", target_work_id="W4",
                     source_author_id="1", target_author_id="2", source_api="test"),
            Citation(source_work_id="W5", target_work_id="W6",
                     source_author_id="2", target_author_id="1", source_api="test"),
        ]
        g = build_author_graph(citations)
        assert g.has_edge("1", "2")
        assert g["1"]["2"]["weight"] == 2
        assert g.has_edge("2", "1")
        assert g["2"]["1"]["weight"] == 1

    def test_excludes_self_citations(self):
        citations = [
            Citation(source_work_id="W1", target_work_id="W2",
                     source_author_id="1", target_author_id="1", source_api="test"),
        ]
        g = build_author_graph(citations)
        assert len(g.edges) == 0

    def test_empty_citations(self):
        g = build_author_graph([])
        assert len(g.nodes) == 0
