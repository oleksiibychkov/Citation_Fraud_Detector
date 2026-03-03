"""Neo4jEngine — GraphEngine implementation that delegates to Neo4j GDS."""

from __future__ import annotations

import logging
from typing import Any

from cfd.graph.engine import GraphEngine
from cfd.neo4j.queries import Neo4jQueries

logger = logging.getLogger(__name__)


class Neo4jEngine(GraphEngine):
    """Graph engine backed by Neo4j GDS for scalable graph operations."""

    def __init__(self, driver: Any):
        self._queries = Neo4jQueries(driver)
        self._pagerank_cache: dict[int, float] | None = None
        self._betweenness_cache: dict[int, float] | None = None
        self._louvain_cache: dict[int, int] | None = None

    def eigenvector_centrality(self, node_id: Any) -> float:
        # Neo4j GDS doesn't have direct eigenvector; use PageRank as proxy
        return self.pagerank(node_id)

    def betweenness_centrality(self, node_id: Any) -> float:
        if self._betweenness_cache is None:
            try:
                self._betweenness_cache = self._queries.run_betweenness()
            except Exception:
                logger.warning("Neo4j betweenness failed", exc_info=True)
                self._betweenness_cache = {}
        return self._betweenness_cache.get(node_id, 0.0)

    def pagerank(self, node_id: Any) -> float:
        if self._pagerank_cache is None:
            try:
                self._pagerank_cache = self._queries.run_pagerank()
            except Exception:
                logger.warning("Neo4j pagerank failed", exc_info=True)
                self._pagerank_cache = {}
        return self._pagerank_cache.get(node_id, 0.0)

    def louvain_communities(self) -> dict[Any, int]:
        if self._louvain_cache is None:
            try:
                self._louvain_cache = self._queries.run_louvain()
            except Exception:
                logger.warning("Neo4j louvain failed", exc_info=True)
                self._louvain_cache = {}
        return self._louvain_cache or {}

    def find_cliques(self, min_size: int = 3) -> list[set]:
        # Neo4j doesn't have built-in clique detection;
        # fall back to finding citation rings
        try:
            rings = self._queries.find_citation_rings(min_length=min_size)
            return [set(r.get("ring", [])) for r in rings if len(r.get("ring", [])) >= min_size]
        except Exception:
            logger.warning("Neo4j clique detection failed", exc_info=True)
            return []

    def has_cycle_in_subgraph(self, node_ids: set) -> bool:
        # Use ring detection as proxy
        try:
            rings = self._queries.find_citation_rings(min_length=2, limit=1)
            return len(rings) > 0
        except Exception:
            return False

    def modularity(self, partition: dict[Any, int]) -> float:
        # Not directly available via Neo4j GDS stream API
        # Return 0.0 as placeholder — can be computed post-hoc
        return 0.0

    def community_densities(self, member_set: set) -> tuple[float, float]:
        # Not directly available via Neo4j
        return 0.0, 0.0

    def subgraph_density(self, node_ids: set) -> float:
        return 0.0

    def average_edge_probability(self) -> float:
        return 0.0

    def has_edge(self, u: Any, v: Any) -> bool:
        try:
            return self._queries.has_relationship(u, v)
        except Exception:
            logger.warning("Neo4j has_edge check failed", exc_info=True)
            return False

    def node_count(self) -> int:
        return 0
