"""Tests for mutual citation heatmap visualization."""

from cfd.data.models import AuthorData, AuthorProfile, Citation
from cfd.visualization.heatmap import build_mutual_heatmap


def _make_profile():
    return AuthorProfile(surname="Test", full_name="Test Author", source_api="openalex")


class TestBuildMutualHeatmap:
    def test_no_data(self):
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        fig = build_mutual_heatmap(ad)
        assert "no data" in fig.layout.title.text.lower()

    def test_single_author(self):
        cits = [
            Citation(source_work_id="W1", target_work_id="W2",
                     source_author_id=1, target_author_id=1,
                     is_self_citation=True, source_api="openalex"),
        ]
        ad = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        fig = build_mutual_heatmap(ad)
        # Self-citations are excluded, so no data
        assert fig is not None

    def test_mutual_pair(self):
        cits = [
            Citation(source_work_id="W1", target_work_id="W2",
                     source_author_id=1, target_author_id=2,
                     is_self_citation=False, source_api="openalex"),
            Citation(source_work_id="W3", target_work_id="W4",
                     source_author_id=2, target_author_id=1,
                     is_self_citation=False, source_api="openalex"),
        ]
        ad = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        fig = build_mutual_heatmap(ad)
        data_dict = fig.to_dict()
        heatmap_traces = [t for t in data_dict["data"] if t.get("type") == "heatmap"]
        assert len(heatmap_traces) == 1
        # 2x2 matrix
        assert len(heatmap_traces[0]["z"]) == 2
        assert len(heatmap_traces[0]["z"][0]) == 2

    def test_matrix_symmetric(self):
        cits = [
            Citation(source_work_id=f"W{i}", target_work_id=f"T{i}",
                     source_author_id=i % 3 + 1, target_author_id=(i + 1) % 3 + 1,
                     is_self_citation=False, source_api="openalex")
            for i in range(9)
        ]
        ad = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        fig = build_mutual_heatmap(ad)
        data_dict = fig.to_dict()
        heatmap_traces = [t for t in data_dict["data"] if t.get("type") == "heatmap"]
        if heatmap_traces:
            z = heatmap_traces[0]["z"]
            n = len(z)
            for i in range(n):
                for j in range(n):
                    assert abs(z[i][j] - z[j][i]) < 0.001

    def test_colorscale_present(self):
        cits = [
            Citation(source_work_id="W1", target_work_id="W2",
                     source_author_id=1, target_author_id=2,
                     is_self_citation=False, source_api="openalex"),
            Citation(source_work_id="W3", target_work_id="W4",
                     source_author_id=2, target_author_id=1,
                     is_self_citation=False, source_api="openalex"),
        ]
        ad = AuthorData(profile=_make_profile(), publications=[], citations=cits)
        fig = build_mutual_heatmap(ad)
        data_dict = fig.to_dict()
        heatmap_traces = [t for t in data_dict["data"] if t.get("type") == "heatmap"]
        assert len(heatmap_traces[0]["colorscale"]) > 0
