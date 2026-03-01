"""Neo4j driver singleton (optional dependency)."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from cfd.config.settings import Settings

logger = logging.getLogger(__name__)

_driver: Any | None = None


def get_neo4j_driver(settings: Settings) -> Any | None:
    """Get or create a Neo4j driver instance. Returns None if unavailable."""
    global _driver  # noqa: PLW0603

    if _driver is not None:
        return _driver

    if not settings.neo4j_uri or not settings.neo4j_password:
        return None

    try:
        from neo4j import GraphDatabase

        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        # Verify connectivity
        _driver.verify_connectivity()
        logger.info("Connected to Neo4j at %s", settings.neo4j_uri)
        return _driver
    except ImportError:
        logger.debug("neo4j package not installed")
        return None
    except Exception:
        logger.warning("Failed to connect to Neo4j", exc_info=True)
        _driver = None
        return None


def close_neo4j_driver() -> None:
    """Close the Neo4j driver if it exists."""
    global _driver  # noqa: PLW0603
    if _driver is not None:
        with contextlib.suppress(Exception):
            _driver.close()
        _driver = None
