"""Tests for mutual citation graph construction."""

from cfd.data.models import Citation
from cfd.graph.mutual import build_mutual_graph


def _cit(src: int, tgt: int) -> Citation:
    return Citation(
        source_work_id=f"w-{src}-{tgt}",
        target_work_id=f"t-{src}-{tgt}",
        source_author_id=str(src),
        target_author_id=str(tgt),
        is_self_citation=False,
        source_api="test",
    )


class TestBuildMutualGraph:
    def test_mutual_edge_created(self):
        """Two authors citing each other should create an edge."""
        citations = [_cit(1, 2), _cit(2, 1)]
        g = build_mutual_graph(citations, mcr_threshold=0.0)
        assert g.has_edge("1", "2")

    def test_no_mutual_no_edge(self):
        """One-way citation should not create an edge."""
        citations = [_cit(1, 2), _cit(1, 3)]
        g = build_mutual_graph(citations, mcr_threshold=0.0)
        assert not g.has_edge("1", "2")

    def test_threshold_filters(self):
        """High threshold should filter weak mutual citations."""
        # 1 cites 2 once, 2 cites 1 once, but total citations dilute MCR
        citations = [_cit(1, 2), _cit(2, 1), _cit(1, 3), _cit(1, 4), _cit(1, 5)]
        g_low = build_mutual_graph(citations, mcr_threshold=0.0)
        g_high = build_mutual_graph(citations, mcr_threshold=0.5)
        assert g_low.has_edge("1", "2")
        assert not g_high.has_edge("1", "2")

    def test_self_citations_ignored(self):
        """Self-citations (src == tgt) should be ignored."""
        citations = [
            Citation(
                source_work_id="w1", target_work_id="t1",
                source_author_id="1", target_author_id="1",
                is_self_citation=True, source_api="test",
            ),
        ]
        g = build_mutual_graph(citations, mcr_threshold=0.0)
        assert len(g.edges) == 0

    def test_empty_citations(self):
        g = build_mutual_graph([], mcr_threshold=0.0)
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_edge_weight_is_mcr(self):
        """Edge weight should be the MCR value."""
        citations = [_cit(1, 2), _cit(2, 1)]
        g = build_mutual_graph(citations, mcr_threshold=0.0)
        assert g["1"]["2"]["mcr"] > 0
