"""OpenAlex data collection for organization-level analysis."""

from __future__ import annotations

import contextlib
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from cfd.data.http_client import CachedHttpClient

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org"


@dataclass
class InstitutionProfile:
    """Institution profile from OpenAlex."""

    openalex_id: str
    display_name: str
    ror: str | None = None
    country_code: str | None = None
    type: str | None = None
    homepage_url: str | None = None
    works_count: int = 0
    cited_by_count: int = 0
    authors_count: int = 0


@dataclass
class AffiliatedAuthor:
    """Author affiliated with an institution."""

    openalex_id: str
    display_name: str
    orcid: str | None = None
    scopus_id: str | None = None
    h_index: int | None = None
    works_count: int = 0
    cited_by_count: int = 0
    last_known_institution: str | None = None
    # Per-period stats (filled by fetch_author_works_in_period)
    works_in_period: int = 0
    scopus_indexed_in_period: int = 0
    works_in_period_list: list[dict] = field(default_factory=list)


@dataclass
class OrganizationData:
    """Complete organization data collection result."""

    institution: InstitutionProfile
    authors: list[AffiliatedAuthor] = field(default_factory=list)
    period_from: date | None = None
    period_to: date | None = None
    total_works_in_period: int = 0
    total_scopus_indexed: int = 0


class OrganizationCollector:
    """Collect organization data from OpenAlex."""

    def __init__(self, http_client: CachedHttpClient, polite_email: str | None = None):
        self._http = http_client
        self._polite_email = polite_email

    def _params(self, extra: dict | None = None) -> dict:
        params = {}
        if self._polite_email:
            params["mailto"] = self._polite_email
        if extra:
            params.update(extra)
        return params

    def fetch_institution(self, query: str, *, ror: str | None = None) -> InstitutionProfile:
        """Fetch institution profile from OpenAlex."""
        if ror:
            # Direct lookup by ROR
            params = self._params()
            data = self._http.get(
                f"{BASE_URL}/institutions/ror:{ror}",
                params=params,
                source_api="openalex",
            )
            return self._parse_institution(data)

        # Search by name
        params = self._params({"search": query})
        data = self._http.get(f"{BASE_URL}/institutions", params=params, source_api="openalex")
        results = data.get("results", [])
        if not results:
            raise ValueError(f"Institution not found: {query}")
        return self._parse_institution(results[0])

    def _parse_institution(self, data: dict) -> InstitutionProfile:
        openalex_id = (data.get("id") or "").replace("https://openalex.org/", "")
        ids = data.get("ids") or {}
        ror = ids.get("ror") or data.get("ror")

        summary = data.get("summary_stats") or {}

        return InstitutionProfile(
            openalex_id=openalex_id,
            display_name=data.get("display_name") or "",
            ror=ror,
            country_code=data.get("country_code"),
            type=data.get("type"),
            homepage_url=data.get("homepage_url"),
            works_count=data.get("works_count") or 0,
            cited_by_count=data.get("cited_by_count") or 0,
            authors_count=data.get("works_api_url", "").count("author") or 0,
        )

    def fetch_affiliated_authors(
        self,
        institution_id: str,
        *,
        max_authors: int = 1000,
    ) -> list[AffiliatedAuthor]:
        """Fetch all authors affiliated with the institution."""
        authors: list[AffiliatedAuthor] = []
        cursor = "*"
        per_page = 200

        while cursor and len(authors) < max_authors:
            params = self._params({
                "filter": f"last_known_institutions.id:{institution_id}",
                "per_page": str(per_page),
                "cursor": cursor,
                "sort": "cited_by_count:desc",
                "select": "id,display_name,ids,summary_stats,works_count,"
                "cited_by_count,last_known_institutions",
            })

            data = self._http.get(f"{BASE_URL}/authors", params=params, source_api="openalex")

            for author_data in data.get("results", []):
                author = self._parse_author(author_data)
                if author:
                    authors.append(author)

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")
            if not data.get("results"):
                break

        logger.info("Fetched %d authors for institution %s", len(authors), institution_id)
        return authors

    def _parse_author(self, data: dict) -> AffiliatedAuthor | None:
        openalex_id = (data.get("id") or "").replace("https://openalex.org/", "")
        if not openalex_id:
            return None

        ids = data.get("ids") or {}
        orcid = ids.get("orcid") or ""
        if orcid:
            orcid = orcid.replace("https://orcid.org/", "")
        scopus_id = ids.get("scopus") or ""
        if scopus_id:
            scopus_id = scopus_id.replace(
                "https://www.scopus.com/authid/detail.uri?authorId=", "",
            )

        summary = data.get("summary_stats") or {}
        institutions = data.get("last_known_institutions") or []
        last_inst = institutions[0].get("display_name") if institutions else None

        return AffiliatedAuthor(
            openalex_id=openalex_id,
            display_name=data.get("display_name") or "",
            orcid=orcid or None,
            scopus_id=scopus_id or None,
            h_index=summary.get("h_index"),
            works_count=data.get("works_count") or 0,
            cited_by_count=data.get("cited_by_count") or 0,
            last_known_institution=last_inst,
        )

    def fetch_author_works_in_period(
        self,
        author: AffiliatedAuthor,
        date_from: date,
        date_to: date,
    ) -> None:
        """Fetch works for an author in a specific period. Updates author in-place."""
        cursor = "*"
        per_page = 200
        works: list[dict] = []

        filter_str = (
            f"author.id:{author.openalex_id},"
            f"from_publication_date:{date_from.isoformat()},"
            f"to_publication_date:{date_to.isoformat()}"
        )

        while cursor:
            params = self._params({
                "filter": filter_str,
                "per_page": str(per_page),
                "cursor": cursor,
                "select": "id,doi,title,publication_date,primary_location,type",
            })

            try:
                data = self._http.get(f"{BASE_URL}/works", params=params, source_api="openalex")
            except Exception:
                logger.warning("Failed to fetch works for %s", author.display_name, exc_info=True)
                break

            for work in data.get("results", []):
                work_id = (work.get("id") or "").replace("https://openalex.org/", "")
                if not work_id:
                    continue

                pub_date = None
                date_str = work.get("publication_date")
                if date_str:
                    with contextlib.suppress(ValueError):
                        pub_date = date.fromisoformat(date_str)

                location = work.get("primary_location") or {}
                source = location.get("source") or {}
                journal_name = source.get("display_name")
                source_type = source.get("type") or ""

                # Check if Scopus-indexed: source has ISSN and type is "journal"
                is_scopus = bool(
                    source_type == "journal"
                    and source.get("issn_l")
                )

                works.append({
                    "work_id": work_id,
                    "doi": work.get("doi"),
                    "title": work.get("title"),
                    "publication_date": pub_date.isoformat() if pub_date else None,
                    "journal": journal_name,
                    "type": work.get("type"),
                    "is_scopus_indexed": is_scopus,
                })

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")
            if not data.get("results"):
                break

        author.works_in_period = len(works)
        author.scopus_indexed_in_period = sum(1 for w in works if w.get("is_scopus_indexed"))
        author.works_in_period_list = works

    def collect_organization(
        self,
        query: str,
        *,
        ror: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        max_authors: int = 500,
        fetch_works: bool = True,
        progress_callback=None,
    ) -> OrganizationData:
        """Full organization data collection pipeline."""
        if date_from is None:
            date_from = date(date.today().year - 1, 1, 1)
        if date_to is None:
            date_to = date.today()

        # Step 1: Fetch institution
        institution = self.fetch_institution(query, ror=ror)

        # Step 2: Fetch affiliated authors
        authors = self.fetch_affiliated_authors(institution.openalex_id, max_authors=max_authors)
        institution.authors_count = len(authors)

        # Step 3: Fetch works per author in period
        if fetch_works:
            for i, author in enumerate(authors):
                if progress_callback:
                    progress_callback(i, len(authors), author.display_name)
                self.fetch_author_works_in_period(author, date_from, date_to)

        total_works = sum(a.works_in_period for a in authors)
        total_scopus = sum(a.scopus_indexed_in_period for a in authors)

        return OrganizationData(
            institution=institution,
            authors=authors,
            period_from=date_from,
            period_to=date_to,
            total_works_in_period=total_works,
            total_scopus_indexed=total_scopus,
        )
