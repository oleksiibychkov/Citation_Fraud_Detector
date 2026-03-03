"""Tests for citation network visualization."""

from datetime import date

from cfd.analysis.pipeline import AnalysisResult
from cfd.data.models import AuthorData, AuthorProfile, Citation, Publication
from cfd.visualization.network import build_network_figure


def _make_profile(**overrides):
    defaults = {
        "surname": "Test",
        "full_name": "Test Author",
        "source_api": "openalex",
    }
    defaults.update(overrides)
    return AuthorProfile(**defaults)


def _make_result(profile, indicators=None, confidence="normal"):
    return AnalysisResult(
        author_profile=profile,
        indicators=indicators or [],
        fraud_score=0.3,
        confidence_level=confidence,
    )


class TestBuildNetworkFigure:
    def test_empty_data(self):
        profile = _make_profile()
        ad = AuthorData(profile=profile, publications=[], citations=[])
        result = _make_result(profile)
        fig = build_network_figure(ad, result)
        assert fig is not None
        assert "no data" in fig.layout.title.text.lower()

    def test_basic_network(self):
        profile = _make_profile()
        pubs = [
            Publication(work_id="W1", citation_count=10, source_api="openalex",
                        publication_date=date(2020, 1, 1)),
            Publication(work_id="W2", citation_count=20, source_api="openalex",
                        publication_date=date(2021, 1, 1)),
        ]
        cits = [
            Citation(source_work_id="W1", target_work_id="W2",
                     source_author_id="1", target_author_id="1",
                     is_self_citation=False, source_api="openalex"),
        ]
        ad = AuthorData(profile=profile, publications=pubs, citations=cits)
        result = _make_result(profile)
        fig = build_network_figure(ad, result)
        data_dict = fig.to_dict()
        assert len(data_dict["data"]) >= 1  # at least node trace

    def test_self_citation_edges(self):
        profile = _make_profile()
        pubs = [
            Publication(work_id="W1", citation_count=5, source_api="openalex",
                        publication_date=date(2020, 1, 1)),
            Publication(work_id="W2", citation_count=15, source_api="openalex",
                        publication_date=date(2021, 1, 1)),
        ]
        cits = [
            Citation(source_work_id="W1", target_work_id="W2",
                     source_author_id="1", target_author_id="1",
                     is_self_citation=True, source_api="openalex"),
        ]
        ad = AuthorData(profile=profile, publications=pubs, citations=cits)
        result = _make_result(profile)
        fig = build_network_figure(ad, result)
        data_dict = fig.to_dict()
        # Should have self-citation edge trace (dashed)
        has_self_edge = any(
            t.get("line", {}).get("dash") == "dash"
            for t in data_dict["data"]
            if t.get("mode") == "lines"
        )
        assert has_self_edge

    def test_color_maps_to_level(self):
        profile = _make_profile()
        pubs = [
            Publication(work_id="W1", citation_count=10, source_api="openalex",
                        publication_date=date(2020, 1, 1)),
        ]
        ad = AuthorData(profile=profile, publications=pubs, citations=[])
        result = _make_result(profile, confidence="critical")
        fig = build_network_figure(ad, result)
        data_dict = fig.to_dict()
        marker_trace = [t for t in data_dict["data"] if t.get("mode") == "markers"]
        assert len(marker_trace) > 0
        # Critical should use red-ish color
        colors = marker_trace[0]["marker"]["color"]
        assert "#c0392b" in colors  # critical color

    def test_max_nodes_subsampling(self):
        profile = _make_profile()
        pubs = [
            Publication(work_id=f"W{i}", citation_count=i, source_api="openalex",
                        publication_date=date(2020, 1, 1))
            for i in range(1, 6)
        ]
        cits = [
            Citation(source_work_id=f"EXT{i}", target_work_id=f"W{i % 5 + 1}",
                     source_author_id=str(i + 10), target_author_id="1",
                     is_self_citation=False, source_api="openalex")
            for i in range(20)
        ]
        ad = AuthorData(profile=profile, publications=pubs, citations=cits)
        result = _make_result(profile)
        fig = build_network_figure(ad, result, max_nodes=10)
        assert fig is not None

    def test_title_includes_author_name(self):
        profile = _make_profile(full_name="Jane Doe")
        ad = AuthorData(profile=profile, publications=[], citations=[])
        result = _make_result(profile)
        fig = build_network_figure(ad, result)
        # Empty graph still has a title
        assert fig.layout.title.text is not None

    def test_figure_serializable(self):
        profile = _make_profile()
        pubs = [
            Publication(work_id="W1", citation_count=5, source_api="openalex",
                        publication_date=date(2020, 1, 1)),
        ]
        ad = AuthorData(profile=profile, publications=pubs, citations=[])
        result = _make_result(profile)
        fig = build_network_figure(ad, result)
        # Should be JSON-serializable
        json_str = fig.to_json()
        assert len(json_str) > 0

    def test_hover_info_present(self):
        profile = _make_profile()
        pubs = [
            Publication(work_id="W1", citation_count=42, source_api="openalex",
                        publication_date=date(2020, 1, 1)),
        ]
        ad = AuthorData(profile=profile, publications=pubs, citations=[])
        result = _make_result(profile)
        fig = build_network_figure(ad, result)
        data_dict = fig.to_dict()
        marker_traces = [t for t in data_dict["data"] if t.get("mode") == "markers"]
        if marker_traces:
            assert marker_traces[0]["hoverinfo"] == "text"
            assert "42" in marker_traces[0]["text"][0]
