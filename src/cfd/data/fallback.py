"""Fallback strategy that switches to secondary API on failure."""

from __future__ import annotations

import logging

from cfd.data.models import AuthorProfile, Citation, Publication
from cfd.data.strategy import DataSourceStrategy
from cfd.exceptions import APIError, AuthorNotFoundError

logger = logging.getLogger(__name__)


class FallbackStrategy(DataSourceStrategy):
    """Strategy that tries primary source first, falls back to secondary on error."""

    def __init__(self, primary: DataSourceStrategy, secondary: DataSourceStrategy):
        self._primary = primary
        self._secondary = secondary

    def fetch_author(
        self,
        surname: str,
        *,
        scopus_id: str | None = None,
        orcid: str | None = None,
    ) -> AuthorProfile:
        try:
            return self._primary.fetch_author(surname, scopus_id=scopus_id, orcid=orcid)
        except (APIError, AuthorNotFoundError) as e:
            logger.warning("Primary API failed for '%s': %s. Switching to secondary.", surname, e)
            return self._secondary.fetch_author(surname, scopus_id=scopus_id, orcid=orcid)

    def fetch_publications(self, author: AuthorProfile) -> list[Publication]:
        try:
            return self._primary.fetch_publications(author)
        except APIError as e:
            logger.warning("Primary API failed for publications: %s. Switching to secondary.", e)
            return self._secondary.fetch_publications(author)

    def fetch_citations(self, publications: list[Publication], author: AuthorProfile) -> list[Citation]:
        try:
            return self._primary.fetch_citations(publications, author)
        except APIError as e:
            logger.warning("Primary API failed for citations: %s. Switching to secondary.", e)
            return self._secondary.fetch_citations(publications, author)
