"""Graph engine abstraction for dual-mode operation (NetworkX / igraph / Neo4j)."""

from __future__ import annotations

import abc
import logging
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class GraphEngine(abc.ABC):
    """Abstract interface for graph operations."""

    @abc.abstractmethod
    def eigenvector_centrality(self, node_id: Any) -> float: ...

    @abc.abstractmethod
    def betweenness_centrality(self, node_id: Any) -> float: ...

    @abc.abstractmethod
    def pagerank(self, node_id: Any) -> float: ...

    @abc.abstractmethod
    def louvain_communities(self) -> dict[Any, int]:
        """Return mapping node_id -> community_id."""
        ...

    @abc.abstractmethod
    def find_cliques(self, min_size: int = 3) -> list[set]: ...

    @abc.abstractmethod
    def has_cycle_in_subgraph(self, node_ids: set) -> bool: ...

    @abc.abstractmethod
    def modularity(self, partition: dict[Any, int]) -> float: ...

    @abc.abstractmethod
    def community_densities(self, member_set: set) -> tuple[float, float]:
        """Return (internal_density, external_density) for a community."""
        ...

    @abc.abstractmethod
    def subgraph_density(self, node_ids: set) -> float: ...

    @abc.abstractmethod
    def average_edge_probability(self) -> float: ...

    @abc.abstractmethod
    def node_count(self) -> int: ...

    @abc.abstractmethod
    def has_edge(self, u: Any, v: Any) -> bool:
        """Check if a directed edge u→v exists."""
        ...


class NetworkXEngine(GraphEngine):
    """Pure NetworkX implementation of graph operations."""

    def __init__(self, graph: nx.DiGraph | nx.Graph):
        self._g = graph
        self._undirected = graph.to_undirected() if graph.is_directed() else graph
        self._eigen_cache: dict | None = None
        self._between_cache: dict | None = None
        self._pr_cache: dict | None = None

    def eigenvector_centrality(self, node_id: Any) -> float:
        if self._eigen_cache is None:
            try:
                self._eigen_cache = nx.eigenvector_centrality(
                    self._undirected, max_iter=1000, weight="weight"
                )
            except (nx.PowerIterationFailedConvergence, nx.NetworkXException):
                self._eigen_cache = {}
        return self._eigen_cache.get(node_id, 0.0)

    def betweenness_centrality(self, node_id: Any) -> float:
        if self._between_cache is None:
            self._between_cache = nx.betweenness_centrality(self._g, weight="weight")
        return self._between_cache.get(node_id, 0.0)

    def pagerank(self, node_id: Any) -> float:
        if self._pr_cache is None:
            try:
                self._pr_cache = nx.pagerank(self._g, weight="weight")
            except nx.NetworkXException:
                self._pr_cache = {}
        return self._pr_cache.get(node_id, 0.0)

    def louvain_communities(self) -> dict[Any, int]:
        from networkx.algorithms.community import louvain_communities

        communities = louvain_communities(self._undirected, weight="weight", seed=42)
        node_to_community: dict[Any, int] = {}
        for cid, members in enumerate(communities):
            for node in members:
                node_to_community[node] = cid
        return node_to_community

    def find_cliques(self, min_size: int = 3) -> list[set]:
        return [set(c) for c in nx.find_cliques(self._undirected) if len(c) >= min_size]

    def has_cycle_in_subgraph(self, node_ids: set) -> bool:
        sub = self._g.subgraph(node_ids)
        if sub.is_directed():
            return not nx.is_directed_acyclic_graph(sub)
        return bool(nx.cycle_basis(sub))

    def modularity(self, partition: dict[Any, int]) -> float:
        communities_list: dict[int, set] = {}
        for node, cid in partition.items():
            communities_list.setdefault(cid, set()).add(node)
        return nx.algorithms.community.quality.modularity(
            self._undirected, communities_list.values()
        )

    def community_densities(self, member_set: set) -> tuple[float, float]:
        all_nodes = set(self._undirected.nodes)
        outside = all_nodes - member_set

        internal_edges = 0
        external_edges = 0
        for u, v in self._undirected.edges:
            u_in = u in member_set
            v_in = v in member_set
            if u_in and v_in:
                internal_edges += 1
            elif u_in or v_in:
                external_edges += 1

        n_members = len(member_set)
        n_outside = len(outside)

        max_internal = n_members * (n_members - 1) / 2 if n_members > 1 else 1
        max_external = n_members * n_outside if n_outside > 0 else 1

        return internal_edges / max_internal, external_edges / max_external

    def subgraph_density(self, node_ids: set) -> float:
        sub = self._undirected.subgraph(node_ids)
        return nx.density(sub)

    def average_edge_probability(self) -> float:
        n = len(self._undirected.nodes)
        if n < 2:
            return 0.0
        max_edges = n * (n - 1) / 2
        return len(self._undirected.edges) / max_edges

    def node_count(self) -> int:
        return len(self._g.nodes)

    def has_edge(self, u: Any, v: Any) -> bool:
        return self._g.has_edge(u, v)


def select_engine(graph: nx.DiGraph | nx.Graph, threshold: int = 50_000) -> GraphEngine:
    """Auto-select the best local engine based on graph size."""
    n = len(graph.nodes)
    if n > threshold:
        try:
            from cfd.graph.igraph_engine import IGraphEngine

            return IGraphEngine(graph)
        except ImportError:
            logger.warning("igraph not installed; using NetworkX for %d nodes", n)
    return NetworkXEngine(graph)
