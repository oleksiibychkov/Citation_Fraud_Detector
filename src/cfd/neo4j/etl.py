"""ETL: Supabase PostgreSQL → Neo4j sync."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class Neo4jETL:
    """Sync author, publication, and citation data from Supabase to Neo4j."""

    def __init__(self, driver: Any):
        self._driver = driver

    def sync_author(self, author: dict) -> None:
        """MERGE an Author node."""
        query = """
        MERGE (a:Author {author_id: $author_id})
        SET a.scopus_id = $scopus_id,
            a.orcid = $orcid,
            a.surname = $surname,
            a.full_name = $full_name,
            a.institution = $institution
        """
        with self._driver.session() as session:
            session.run(
                query,
                author_id=author.get("id"),
                scopus_id=author.get("scopus_id"),
                orcid=author.get("orcid"),
                surname=author.get("surname"),
                full_name=author.get("full_name"),
                institution=author.get("institution"),
            )

    def sync_publication(self, pub: dict, author_id: int) -> None:
        """MERGE a Publication node and link to Author."""
        query = """
        MERGE (p:Publication {work_id: $work_id})
        SET p.doi = $doi, p.title = $title
        WITH p
        MATCH (a:Author {author_id: $author_id})
        MERGE (a)-[:AUTHORED]->(p)
        """
        with self._driver.session() as session:
            session.run(
                query,
                work_id=pub.get("work_id"),
                doi=pub.get("doi"),
                title=pub.get("title"),
                author_id=author_id,
            )

    def sync_citation(self, citation: dict) -> None:
        """MERGE a CITES relationship between authors."""
        query = """
        MATCH (src:Author {author_id: $source_author_id})
        MATCH (tgt:Author {author_id: $target_author_id})
        MERGE (src)-[r:CITES]->(tgt)
        ON CREATE SET r.weight = 1
        ON MATCH SET r.weight = r.weight + 1
        """
        src = citation.get("source_author_id")
        tgt = citation.get("target_author_id")
        if src and tgt and src != tgt:
            with self._driver.session() as session:
                session.run(query, source_author_id=src, target_author_id=tgt)

    def sync_batch(self, authors: list[dict], publications: list[dict], citations: list[dict]) -> None:
        """Sync a batch of data."""
        for author in authors:
            self.sync_author(author)
        for pub in publications:
            self.sync_publication(pub, pub.get("author_id"))
        for cit in citations:
            self.sync_citation(cit)
        logger.info(
            "Synced to Neo4j: %d authors, %d publications, %d citations",
            len(authors), len(publications), len(citations),
        )
