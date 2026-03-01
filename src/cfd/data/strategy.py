"""Abstract base class for data source strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from cfd.data.models import AuthorData, AuthorProfile, Citation, Publication


class DataSourceStrategy(ABC):
    """Abstract strategy for fetching author data from a scientometric API."""

    @abstractmethod
    def fetch_author(
        self,
        surname: str,
        *,
        scopus_id: str | None = None,
        orcid: str | None = None,
    ) -> AuthorProfile:
        """Fetch author profile. Raises AuthorNotFoundError if not found."""
        ...

    @abstractmethod
    def fetch_publications(self, author: AuthorProfile) -> list[Publication]:
        """Fetch all publications for an author."""
        ...

    @abstractmethod
    def fetch_citations(self, publications: list[Publication], author: AuthorProfile) -> list[Citation]:
        """Fetch citation relationships for all publications."""
        ...

    def collect(
        self,
        surname: str,
        *,
        scopus_id: str | None = None,
        orcid: str | None = None,
    ) -> AuthorData:
        """Full data collection pipeline for one author."""
        profile = self.fetch_author(surname, scopus_id=scopus_id, orcid=orcid)
        publications = self.fetch_publications(profile)
        citations = self.fetch_citations(publications, profile)
        return AuthorData(
            profile=profile,
            publications=publications,
            citations=citations,
        )
