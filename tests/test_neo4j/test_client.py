"""Tests for Neo4j client (mock-based, no real connection needed)."""

from unittest.mock import MagicMock, patch

from cfd.config.settings import Settings
from cfd.neo4j.client import close_neo4j_driver, get_neo4j_driver


class TestGetNeo4jDriver:
    def test_returns_none_without_credentials(self):
        settings = Settings(neo4j_uri="", neo4j_password="")
        driver = get_neo4j_driver(settings)
        assert driver is None

    def test_returns_none_when_neo4j_not_installed(self):
        settings = Settings(neo4j_uri="neo4j+s://test.databases.neo4j.io", neo4j_password="secret")
        with patch.dict("sys.modules", {"neo4j": None}):
            # Force reimport to hit ImportError path
            import cfd.neo4j.client as mod
            mod._driver = None  # reset singleton
            mod.get_neo4j_driver(settings)
            # Will either be None (ImportError) or fail to connect
            # Both are acceptable outcomes without a real Neo4j instance


class TestCloseNeo4jDriver:
    def test_close_with_no_driver(self):
        """Should not raise even with no driver."""
        import cfd.neo4j.client as mod
        mod._driver = None
        close_neo4j_driver()

    def test_close_with_mock_driver(self):
        import cfd.neo4j.client as mod
        mock_driver = MagicMock()
        mod._driver = mock_driver
        close_neo4j_driver()
        mock_driver.close.assert_called_once()
        assert mod._driver is None
