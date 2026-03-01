"""Tests for Neo4j ETL (mock-based)."""

from unittest.mock import MagicMock

from cfd.neo4j.etl import Neo4jETL


class TestNeo4jETL:
    def _make_etl(self):
        driver = MagicMock()
        session = MagicMock()
        driver.session.return_value.__enter__ = MagicMock(return_value=session)
        driver.session.return_value.__exit__ = MagicMock(return_value=False)
        return Neo4jETL(driver), session

    def test_sync_author(self):
        etl, session = self._make_etl()
        etl.sync_author({"id": 1, "scopus_id": "123", "surname": "Test"})
        session.run.assert_called_once()

    def test_sync_publication(self):
        etl, session = self._make_etl()
        etl.sync_publication({"work_id": "w1", "doi": "10.1/test", "title": "Test"}, author_id=1)
        session.run.assert_called_once()

    def test_sync_citation(self):
        etl, session = self._make_etl()
        etl.sync_citation({"source_author_id": 1, "target_author_id": 2})
        session.run.assert_called_once()

    def test_sync_citation_skips_self(self):
        etl, session = self._make_etl()
        etl.sync_citation({"source_author_id": 1, "target_author_id": 1})
        session.run.assert_not_called()

    def test_sync_batch(self):
        etl, session = self._make_etl()
        etl.sync_batch(
            authors=[{"id": 1, "surname": "A"}],
            publications=[{"work_id": "w1", "author_id": 1}],
            citations=[{"source_author_id": 1, "target_author_id": 2}],
        )
        assert session.run.call_count == 3
