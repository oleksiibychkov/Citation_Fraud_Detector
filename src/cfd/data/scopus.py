"""Scopus API data source strategy."""

from __future__ import annotations

import contextlib
import logging
from datetime import date

from cfd.data.http_client import CachedHttpClient
from cfd.data.models import AuthorProfile, Citation, Publication
from cfd.data.strategy import DataSourceStrategy
from cfd.data.validators import check_surname_match
from cfd.exceptions import AuthorNotFoundError, IdentityMismatchError, ValidationError

logger = logging.getLogger(__name__)

SCOPUS_BASE = "https://api.elsevier.com/content"


def _safe_int(val) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


class ScopusStrategy(DataSourceStrategy):
    """Data source strategy for Scopus API."""

    def __init__(self, http_client: CachedHttpClient, api_key: str):
        if not api_key:
            raise ValidationError("Scopus API key is required")
        self._http = http_client
        self._api_key = api_key

    def _headers(self) -> dict:
        return {
            "X-ELS-APIKey": self._api_key,
            "Accept": "application/json",
        }

    def fetch_author(
        self,
        surname: str,
        *,
        scopus_id: str | None = None,
        orcid: str | None = None,
    ) -> AuthorProfile:
        """Fetch author profile from Scopus."""
        author_data = None

        # Identity cross-check: when both IDs provided, fetch by both
        # and verify they resolve to the same person (§1.3)
        if scopus_id and orcid:
            data_by_scopus = self._fetch_by_scopus_id(scopus_id)
            data_by_orcid = self._fetch_by_orcid(orcid)
            if data_by_scopus and data_by_orcid:
                self._verify_identity_match(data_by_scopus, data_by_orcid, scopus_id, orcid)
            author_data = data_by_scopus or data_by_orcid
        elif scopus_id:
            author_data = self._fetch_by_scopus_id(scopus_id)
        elif orcid:
            author_data = self._fetch_by_orcid(orcid)
        else:
            author_data = self._fetch_by_name(surname)

        if author_data is None:
            raise AuthorNotFoundError(
                f"Author not found in Scopus: {surname}. "
                "This may happen if the Scopus API key is invalid or restricted to "
                "your institution's IP range (Render.com IPs are not in that range). "
                "Try 'auto' or 'openalex' data source, or use an Institutional Token (insttoken)."
            )

        profile = self._parse_author(author_data, surname)

        match, warning = check_surname_match(surname, profile.full_name or "")
        if not match:
            logger.warning(warning)

        return profile

    @staticmethod
    def _verify_identity_match(
        data_by_scopus: dict, data_by_orcid: dict, scopus_id: str, orcid: str,
    ) -> None:
        """Verify that Scopus ID and ORCID resolve to the same Scopus author."""
        id_a = data_by_scopus.get("coredata", {}).get("dc:identifier", "").replace("AUTHOR_ID:", "")
        id_b = data_by_orcid.get("coredata", {}).get("dc:identifier", "").replace("AUTHOR_ID:", "")
        if id_a and id_b and id_a != id_b:
            raise IdentityMismatchError(
                f"Scopus ID {scopus_id} resolves to author {id_a} but ORCID {orcid} "
                f"resolves to author {id_b} — these appear to be different authors"
            )

    def _fetch_by_scopus_id(self, scopus_id: str) -> dict | None:
        url = f"{SCOPUS_BASE}/author/author_id/{scopus_id}"
        try:
            data = self._http.get(url, headers=self._headers(), source_api="scopus")
            return data.get("author-retrieval-response", [{}])[0]
        except Exception:
            logger.warning("Scopus: failed to fetch author by ID %s", scopus_id, exc_info=True)
            return None

    def _fetch_by_orcid(self, orcid: str) -> dict | None:
        url = f"{SCOPUS_BASE}/search/author"
        params = {"query": f"orcid({orcid})"}
        try:
            data = self._http.get(url, params=params, headers=self._headers(), source_api="scopus")
            results = data.get("search-results", {}).get("entry", [])
            if results and results[0].get("dc:identifier"):
                author_id = results[0]["dc:identifier"].replace("AUTHOR_ID:", "")
                return self._fetch_by_scopus_id(author_id)
        except Exception:
            logger.warning("Scopus: failed to fetch author by ORCID %s", orcid, exc_info=True)
        return None

    def _fetch_by_name(self, name: str) -> dict | None:
        url = f"{SCOPUS_BASE}/search/author"
        params = {"query": f"authlast({name})"}
        try:
            data = self._http.get(url, params=params, headers=self._headers(), source_api="scopus")
            results = data.get("search-results", {}).get("entry", [])
            if results and results[0].get("dc:identifier"):
                author_id = results[0]["dc:identifier"].replace("AUTHOR_ID:", "")
                return self._fetch_by_scopus_id(author_id)
        except Exception:
            logger.warning("Scopus: failed to fetch author by name %s", name, exc_info=True)
        return None

    def _parse_author(self, data: dict, surname: str) -> AuthorProfile:
        """Parse Scopus author retrieval response."""
        core = data.get("coredata", {})
        profile_data = data.get("author-profile", {})
        preferred_name = profile_data.get("preferred-name", {})

        full_name = f"{preferred_name.get('given-name', '')} {preferred_name.get('surname', '')}".strip()
        scopus_id = core.get("dc:identifier", "").replace("AUTHOR_ID:", "")

        # Get ORCID if available
        orcid = None
        for id_entry in data.get("coredata", {}).get("link", []):
            if "orcid" in str(id_entry.get("@href", "")):
                orcid = id_entry.get("@href", "").split("/")[-1]

        # Institution
        institution = None
        affiliation_history = profile_data.get("affiliation-history", {}).get("affiliation", [])
        if affiliation_history:
            if isinstance(affiliation_history, dict):
                affiliation_history = [affiliation_history]
            institution = affiliation_history[0].get("ip-doc", {}).get("afdispname")

        # Subject areas
        subject_areas = data.get("subject-areas", {}).get("subject-area", [])
        discipline = subject_areas[0].get("$") if subject_areas else None

        return AuthorProfile(
            scopus_id=scopus_id or None,
            orcid=orcid,
            surname=surname,
            full_name=full_name or None,
            institution=institution,
            discipline=discipline,
            h_index=_safe_int(core.get("h-index")),
            publication_count=_safe_int(core.get("document-count")),
            citation_count=_safe_int(core.get("citation-count")),
            source_api="scopus",
            raw_data=data,
        )

    def fetch_publications(self, author: AuthorProfile) -> list[Publication]:
        """Fetch publications from Scopus Search API."""
        if not author.scopus_id:
            return []

        publications = []
        start = 0
        count = 25

        while True:
            url = f"{SCOPUS_BASE}/search/scopus"
            params = {
                "query": f"AU-ID({author.scopus_id})",
                "count": str(count),
                "start": str(start),
            }
            try:
                data = self._http.get(url, params=params, headers=self._headers(), source_api="scopus")
            except Exception:
                logger.warning("Failed to fetch Scopus publications at offset %d", start)
                break

            entries = data.get("search-results", {}).get("entry", [])
            if not entries:
                break

            for entry in entries:
                pub = self._parse_publication(entry)
                if pub:
                    publications.append(pub)

            total = _safe_int(data.get("search-results", {}).get("opensearch:totalResults", 0)) or 0
            start += count
            if start >= total:
                break

        logger.info("Fetched %d publications from Scopus for %s", len(publications), author.full_name)
        return publications

    def _parse_publication(self, entry: dict) -> Publication | None:
        """Parse a Scopus search result entry."""
        eid = entry.get("eid", "")
        if not eid:
            return None

        pub_date = None
        date_str = entry.get("prism:coverDate")
        if date_str:
            with contextlib.suppress(ValueError):
                pub_date = date.fromisoformat(date_str)

        return Publication(
            work_id=eid,
            doi=entry.get("prism:doi"),
            title=entry.get("dc:title"),
            publication_date=pub_date,
            journal=entry.get("prism:publicationName"),
            citation_count=_safe_int(entry.get("citedby-count")) or 0,
            source_api="scopus",
            raw_data=entry,
        )

    def fetch_citations(self, publications: list[Publication], author: AuthorProfile) -> list[Citation]:
        """Fetch citation relationships from Scopus. Simplified for MVP."""
        citations = []
        for pub in publications:
            for ref_id in pub.references_list:
                citations.append(
                    Citation(
                        source_work_id=pub.work_id,
                        target_work_id=ref_id,
                        citation_date=pub.publication_date,
                        is_self_citation=False,
                        source_api="scopus",
                    )
                )
        return citations
