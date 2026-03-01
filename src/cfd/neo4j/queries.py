"""Cypher queries for Neo4j graph operations."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class Neo4jQueries:
    """Wrapper for common Cypher queries against Neo4j/GDS."""

    def __init__(self, driver: Any):
        self._driver = driver

    def find_citation_rings(self, min_length: int = 3, limit: int = 100) -> list[dict]:
        """Find citation rings (cycles) in the graph."""
        query = f"""
        MATCH path = (a:Author)-[:CITES*{min_length}..10]->(a)
        WITH [n IN nodes(path) | n.author_id] AS ring
        WHERE size(ring) >= $min_length
        RETURN DISTINCT ring
        LIMIT $limit
        """
        with self._driver.session() as session:
            result = session.run(query, min_length=min_length, limit=limit)
            return [dict(r) for r in result]

    def find_mutual_citations(self, threshold: float = 0.3) -> list[dict]:
        """Find mutually citing author pairs."""
        query = """
        MATCH (a:Author)-[r1:CITES]->(b:Author)-[r2:CITES]->(a)
        WHERE id(a) < id(b)
        WITH a, b, count(r1) AS a_to_b, count(r2) AS b_to_a
        WITH a, b, a_to_b, b_to_a,
             2.0 * toFloat(CASE WHEN a_to_b < b_to_a THEN a_to_b ELSE b_to_a END)
             / (a_to_b + b_to_a) AS mcr
        WHERE mcr > $threshold
        RETURN a.author_id AS author_a, b.author_id AS author_b, mcr
        ORDER BY mcr DESC
        """
        with self._driver.session() as session:
            result = session.run(query, threshold=threshold)
            return [dict(r) for r in result]

    def run_louvain(self) -> dict[int, int]:
        """Run Louvain community detection via GDS (if available)."""
        # Project graph
        self._ensure_graph_projection("cfd_graph")
        query = """
        CALL gds.louvain.stream('cfd_graph')
        YIELD nodeId, communityId
        RETURN gds.util.asNode(nodeId).author_id AS author_id, communityId
        """
        partition = {}
        with self._driver.session() as session:
            result = session.run(query)
            for record in result:
                partition[record["author_id"]] = record["communityId"]
        return partition

    def run_pagerank(self) -> dict[int, float]:
        """Run PageRank via GDS."""
        self._ensure_graph_projection("cfd_graph")
        query = """
        CALL gds.pageRank.stream('cfd_graph')
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).author_id AS author_id, score
        """
        scores = {}
        with self._driver.session() as session:
            result = session.run(query)
            for record in result:
                scores[record["author_id"]] = record["score"]
        return scores

    def run_betweenness(self) -> dict[int, float]:
        """Run Betweenness Centrality via GDS."""
        self._ensure_graph_projection("cfd_graph")
        query = """
        CALL gds.betweenness.stream('cfd_graph')
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).author_id AS author_id, score
        """
        scores = {}
        with self._driver.session() as session:
            result = session.run(query)
            for record in result:
                scores[record["author_id"]] = record["score"]
        return scores

    def _ensure_graph_projection(self, graph_name: str) -> None:
        """Create GDS graph projection if it doesn't exist."""
        check_query = "CALL gds.graph.exists($name) YIELD exists"
        project_query = """
        CALL gds.graph.project($name, 'Author', 'CITES', {relationshipProperties: 'weight'})
        """
        with self._driver.session() as session:
            result = session.run(check_query, name=graph_name)
            exists = result.single()["exists"]
            if not exists:
                session.run(project_query, name=graph_name)
