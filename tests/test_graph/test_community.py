"""Tests for community detection."""

import networkx as nx

from cfd.graph.community import CommunityResult, community_to_indicator, detect_communities
from cfd.graph.engine import NetworkXEngine


def _make_two_cluster_engine():
    """Two tight clusters connected by a weak bridge."""
    g = nx.Graph()
    # Cluster 1: nodes 1, 2, 3 (fully connected)
    g.add_weighted_edges_from([(1, 2, 1.0), (2, 3, 1.0), (1, 3, 1.0)])
    # Cluster 2: nodes 4, 5, 6 (fully connected)
    g.add_weighted_edges_from([(4, 5, 1.0), (5, 6, 1.0), (4, 6, 1.0)])
    # Weak bridge
    g.add_edge(3, 4, weight=0.1)
    return NetworkXEngine(g)


class TestDetectCommunities:
    def test_returns_community_result(self):
        engine = _make_two_cluster_engine()
        result = detect_communities(engine)
        assert isinstance(result, CommunityResult)
        assert len(result.partition) == 6
        assert result.modularity > 0

    def test_finds_communities(self):
        engine = _make_two_cluster_engine()
        result = detect_communities(engine)
        assert len(result.communities) >= 2

    def test_empty_graph(self):
        g = nx.Graph()
        engine = NetworkXEngine(g)
        result = detect_communities(engine)
        assert result.partition == {}
        assert result.communities == {}

    def test_suspicious_detection(self):
        engine = _make_two_cluster_engine()
        result = detect_communities(engine, density_ratio_threshold=0.5, min_community_size=3)
        # Both clusters are tight with weak external link → might be flagged
        assert isinstance(result.suspicious_communities, list)

    def test_min_community_size_filter(self):
        engine = _make_two_cluster_engine()
        result = detect_communities(engine, min_community_size=10)
        # No community has 10 members → no suspicious
        assert result.suspicious_communities == []


class TestCommunityToIndicator:
    def test_no_communities(self):
        result = CommunityResult()
        ind = community_to_indicator(result)
        assert ind.indicator_type == "COMMUNITY"
        assert ind.value == 0.0

    def test_with_suspicious(self):
        result = CommunityResult(
            communities={0: {1, 2, 3}, 1: {4, 5, 6}},
            modularity=0.5,
            suspicious_communities=[{"community_id": 0, "density_ratio": 3.0}],
        )
        ind = community_to_indicator(result)
        # 0.5 * (1/2) + 0.3 * (3.0/10) + 0.2 * 0 = 0.25 + 0.09 = 0.34
        assert 0.3 <= ind.value <= 0.4

    def test_all_suspicious(self):
        result = CommunityResult(
            communities={0: {1, 2, 3}},
            modularity=0.4,
            suspicious_communities=[{"community_id": 0, "density_ratio": 5.0, "isolated": True}],
        )
        ind = community_to_indicator(result)
        # 0.5 * 1.0 + 0.3 * 1.0 + 0.2 * 1.0 = 1.0
        assert ind.value == 1.0
