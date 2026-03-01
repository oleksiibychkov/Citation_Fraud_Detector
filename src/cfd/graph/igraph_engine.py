"""IGraphEngine — optional igraph-backed GraphEngine for large graphs (>50K nodes)."""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx

from cfd.graph.engine import GraphEngine

logger = logging.getLogger(__name__)


class IGraphEngine(GraphEngine):
    """igraph implementation of GraphEngine for scalable operations."""

    def __init__(self, graph: nx.DiGraph | nx.Graph):
        import igraph as ig

        # Convert NetworkX to igraph
        self._nx_graph = graph
        self._undirected_nx = graph.to_undirected() if graph.is_directed() else graph

        # Build igraph graph
        node_list = list(graph.nodes)
        self._node_to_idx = {n: i for i, n in enumerate(node_list)}
        self._idx_to_node = {i: n for i, n in enumerate(node_list)}

        edges = []
        weights = []
        for u, v, data in graph.edges(data=True):
            edges.append((self._node_to_idx[u], self._node_to_idx[v]))
            weights.append(data.get("weight", 1.0))

        self._ig = ig.Graph(
            n=len(node_list),
            edges=edges,
            directed=graph.is_directed(),
        )
        self._ig.es["weight"] = weights
        self._ig.vs["name"] = node_list

        # Undirected version
        if graph.is_directed():
            u_edges = []
            u_weights = []
            for u, v, data in self._undirected_nx.edges(data=True):
                u_edges.append((self._node_to_idx[u], self._node_to_idx[v]))
                u_weights.append(data.get("weight", 1.0))
            self._ig_undirected = ig.Graph(
                n=len(node_list),
                edges=u_edges,
                directed=False,
            )
            self._ig_undirected.es["weight"] = u_weights
            self._ig_undirected.vs["name"] = node_list
        else:
            self._ig_undirected = self._ig

        self._eigen_cache: dict | None = None
        self._between_cache: dict | None = None
        self._pr_cache: dict | None = None

    def eigenvector_centrality(self, node_id: Any) -> float:
        if self._eigen_cache is None:
            try:
                scores = self._ig_undirected.eigenvector_centrality(weights="weight")
                self._eigen_cache = {self._idx_to_node[i]: s for i, s in enumerate(scores)}
            except Exception:
                self._eigen_cache = {}
        return self._eigen_cache.get(node_id, 0.0)

    def betweenness_centrality(self, node_id: Any) -> float:
        if self._between_cache is None:
            scores = self._ig.betweenness(weights="weight")
            # Normalize to [0, 1]
            n = self._ig.vcount()
            norm = (n - 1) * (n - 2) / 2 if n > 2 else 1
            self._between_cache = {self._idx_to_node[i]: s / norm for i, s in enumerate(scores)}
        return self._between_cache.get(node_id, 0.0)

    def pagerank(self, node_id: Any) -> float:
        if self._pr_cache is None:
            scores = self._ig.pagerank(weights="weight")
            self._pr_cache = {self._idx_to_node[i]: s for i, s in enumerate(scores)}
        return self._pr_cache.get(node_id, 0.0)

    def louvain_communities(self) -> dict[Any, int]:
        partition = self._ig_undirected.community_multilevel(weights="weight")
        result = {}
        for cid, members in enumerate(partition):
            for idx in members:
                result[self._idx_to_node[idx]] = cid
        return result

    def find_cliques(self, min_size: int = 3) -> list[set]:
        cliques = self._ig_undirected.cliques(min=min_size)
        return [
            {self._idx_to_node[idx] for idx in c}
            for c in cliques
            if len(c) >= min_size
        ]

    def has_cycle_in_subgraph(self, node_ids: set) -> bool:
        indices = [self._node_to_idx[n] for n in node_ids if n in self._node_to_idx]
        sub = self._ig.subgraph(indices)
        if sub.is_directed():
            return not sub.is_dag()
        return sub.ecount() >= sub.vcount()

    def modularity(self, partition: dict[Any, int]) -> float:
        membership = [0] * self._ig_undirected.vcount()
        for node, cid in partition.items():
            if node in self._node_to_idx:
                membership[self._node_to_idx[node]] = cid
        return self._ig_undirected.modularity(membership, weights="weight")

    def community_densities(self, member_set: set) -> tuple[float, float]:
        # Delegate to NetworkX for simplicity
        from cfd.graph.engine import NetworkXEngine

        nx_engine = NetworkXEngine(self._nx_graph)
        return nx_engine.community_densities(member_set)

    def subgraph_density(self, node_ids: set) -> float:
        indices = [self._node_to_idx[n] for n in node_ids if n in self._node_to_idx]
        sub = self._ig_undirected.subgraph(indices)
        return sub.density()

    def average_edge_probability(self) -> float:
        n = self._ig_undirected.vcount()
        if n < 2:
            return 0.0
        max_edges = n * (n - 1) / 2
        return self._ig_undirected.ecount() / max_edges

    def node_count(self) -> int:
        return self._ig.vcount()
