"""OpenAlex API data source strategy."""

from __future__ import annotations

import contextlib
import logging
from datetime import date

from cfd.data.http_client import CachedHttpClient
from cfd.data.models import AuthorProfile, Citation, Publication
from cfd.data.strategy import DataSourceStrategy
from cfd.data.validators import check_surname_match
from cfd.exceptions import AuthorNotFoundError, IdentityMismatchError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org"


class OpenAlexStrategy(DataSourceStrategy):
    """Data source strategy for OpenAlex API."""

    def __init__(self, http_client: CachedHttpClient, polite_email: str | None = None):
        self._http = http_client
        self._polite_email = polite_email

    def _params(self, extra: dict | None = None) -> dict:
        """Build params dict, adding polite pool email if configured."""
        params = {}
        if self._polite_email:
            params["mailto"] = self._polite_email
        if extra:
            params.update(extra)
        return params

    def fetch_author(
        self,
        surname: str,
        *,
        scopus_id: str | None = None,
        orcid: str | None = None,
    ) -> AuthorProfile:
        """Fetch author from OpenAlex by ORCID, Scopus ID, or name search."""
        author_data = None

        # Identity cross-check: when both ORCID and Scopus ID provided,
        # fetch by both and verify they resolve to the same person (§1.3)
        if orcid and scopus_id:
            data_by_orcid = self._fetch_by_orcid(orcid)
            data_by_scopus = self._fetch_by_scopus_id(scopus_id)
            if data_by_orcid and data_by_scopus:
                self._verify_identity_match(data_by_orcid, data_by_scopus, orcid, scopus_id)
            author_data = data_by_orcid or data_by_scopus
        elif orcid:
            author_data = self._fetch_by_orcid(orcid)
        elif scopus_id:
            author_data = self._fetch_by_scopus_id(scopus_id)

        # Fallback: name search (only when no explicit IDs were provided)
        if author_data is None:
            if orcid or scopus_id:
                raise AuthorNotFoundError(
                    f"Author not found by provided identifiers (ORCID={orcid}, Scopus={scopus_id})"
                )
            author_data = self._fetch_by_name(surname)

        if author_data is None:
            raise AuthorNotFoundError(f"Author not found: {surname}")

        profile = self._parse_author(author_data, surname)

        # Verify surname match
        match, warning = check_surname_match(surname, profile.full_name or "")
        if not match:
            logger.warning(warning)

        return profile

    @staticmethod
    def _verify_identity_match(
        data_a: dict, data_b: dict, orcid: str, scopus_id: str,
    ) -> None:
        """Verify that ORCID and Scopus ID resolve to the same OpenAlex author."""
        id_a = data_a.get("id", "")
        id_b = data_b.get("id", "")
        if id_a and id_b and id_a != id_b:
            raise IdentityMismatchError(
                f"ORCID {orcid} resolves to {id_a} but Scopus ID {scopus_id} "
                f"resolves to {id_b} — these appear to be different authors"
            )

    def _fetch_by_orcid(self, orcid: str) -> dict | None:
        params = self._params({"filter": f"orcid:{orcid}"})
        data = self._http.get(f"{BASE_URL}/authors", params=params, source_api="openalex")
        results = data.get("results", [])
        return results[0] if results else None

    def _fetch_by_scopus_id(self, scopus_id: str) -> dict | None:
        params = self._params({"filter": f"ids.scopus:{scopus_id}"})
        data = self._http.get(f"{BASE_URL}/authors", params=params, source_api="openalex")
        results = data.get("results", [])
        return results[0] if results else None

    def _fetch_by_name(self, name: str) -> dict | None:
        params = self._params({"search": name})
        data = self._http.get(f"{BASE_URL}/authors", params=params, source_api="openalex")
        results = data.get("results", [])
        return results[0] if results else None

    def _parse_author(self, data: dict, surname: str) -> AuthorProfile:
        """Parse OpenAlex author response into AuthorProfile."""
        openalex_id = data.get("id", "").replace("https://openalex.org/", "")

        # Extract external IDs
        ids = data.get("ids", {})
        orcid = ids.get("orcid", "")
        if orcid:
            orcid = orcid.replace("https://orcid.org/", "")
        scopus_id = ids.get("scopus", "")
        if scopus_id:
            scopus_id = scopus_id.replace("https://www.scopus.com/authid/detail.uri?authorId=", "")

        # Extract institution
        affiliations = data.get("affiliations", [])
        institution = None
        if affiliations:
            inst = affiliations[0].get("institution", {})
            institution = inst.get("display_name")

        # Name variants
        display_name = data.get("display_name", "")
        alternatives = data.get("display_name_alternatives", [])
        variants = [display_name] + alternatives if display_name else alternatives

        # Summary stats
        summary = data.get("summary_stats", {})

        return AuthorProfile(
            scopus_id=scopus_id or None,
            orcid=orcid or None,
            openalex_id=openalex_id or None,
            surname=surname,
            full_name=display_name or None,
            display_name_variants=variants,
            institution=institution,
            discipline=self._extract_discipline(data),
            h_index=summary.get("h_index"),
            publication_count=data.get("works_count"),
            citation_count=data.get("cited_by_count"),
            source_api="openalex",
            raw_data=data,
        )

    def _extract_discipline(self, data: dict) -> str | None:
        """Extract primary discipline/topic from author data."""
        topics = data.get("topics", [])
        if topics:
            return topics[0].get("display_name")
        x_concepts = data.get("x_concepts", [])
        if x_concepts:
            return x_concepts[0].get("display_name")
        return None

    def fetch_publications(self, author: AuthorProfile) -> list[Publication]:
        """Fetch all publications for an author, handling pagination."""
        if not author.openalex_id:
            return []

        publications = []
        cursor = "*"
        per_page = 200

        while cursor:
            params = self._params({
                "filter": f"author.id:{author.openalex_id}",
                "per_page": str(per_page),
                "cursor": cursor,
                "select": "id,doi,title,publication_date,primary_location,cited_by_count,"
                "referenced_works,authorships,abstract_inverted_index,type,counts_by_year",
            })
            data = self._http.get(f"{BASE_URL}/works", params=params, source_api="openalex")

            for work in data.get("results", []):
                pub = self._parse_publication(work)
                if pub:
                    publications.append(pub)

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")
            if not data.get("results"):
                break

        logger.info("Fetched %d publications for %s", len(publications), author.full_name)
        return publications

    def _parse_publication(self, work: dict) -> Publication | None:
        """Parse an OpenAlex work into a Publication."""
        work_id = work.get("id", "").replace("https://openalex.org/", "")
        if not work_id:
            return None

        # Extract journal from primary_location
        journal = None
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        journal = source.get("display_name")

        # Parse publication date
        pub_date = None
        date_str = work.get("publication_date")
        if date_str:
            with contextlib.suppress(ValueError):
                pub_date = date.fromisoformat(date_str)

        # Reconstruct abstract from inverted index
        abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))

        # Extract co-authors
        co_authors = self._extract_co_authors(work)

        return Publication(
            work_id=work_id,
            doi=work.get("doi"),
            title=work.get("title"),
            abstract=abstract,
            publication_date=pub_date,
            journal=journal,
            citation_count=work.get("cited_by_count", 0),
            references_list=[
                ref.replace("https://openalex.org/", "") for ref in (work.get("referenced_works") or [])
            ],
            co_authors=co_authors,
            source_api="openalex",
            raw_data=work,
        )

    @staticmethod
    def _extract_co_authors(work: dict) -> list[dict]:
        """Extract co-author info from OpenAlex authorships field."""
        co_authors = []
        for authorship in work.get("authorships", []):
            author_obj = authorship.get("author", {})
            author_id = author_obj.get("id", "").replace("https://openalex.org/", "")
            institutions = authorship.get("institutions", [])
            institution_name = institutions[0].get("display_name") if institutions else None
            co_authors.append({
                "author_id": author_id,
                "display_name": author_obj.get("display_name", ""),
                "institution": institution_name,
                "position": authorship.get("author_position", "middle"),
            })
        return co_authors

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
        """Reconstruct abstract text from OpenAlex inverted index format."""
        if not inverted_index:
            return None
        word_positions: list[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort(key=lambda x: x[0])
        return " ".join(word for _, word in word_positions)

    def fetch_citations(self, publications: list[Publication], author: AuthorProfile) -> list[Citation]:
        """Fetch citation edges: who cites the author's publications."""
        citations = []
        seen_edges: set[tuple[str, str]] = set()
        author_work_ids = {pub.work_id for pub in publications}

        for pub in publications:
            # Self-citations from references_list
            for ref_id in pub.references_list:
                edge_key = (pub.work_id, ref_id)
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                is_self = ref_id in author_work_ids
                citations.append(
                    Citation(
                        source_work_id=pub.work_id,
                        target_work_id=ref_id,
                        citation_date=pub.publication_date,
                        is_self_citation=is_self,
                        source_api="openalex",
                    )
                )

            # Incoming citations (who cites this publication)
            self._fetch_citing_works(pub, citations, author, seen_edges)

        logger.info("Collected %d citation edges for %s", len(citations), author.full_name)
        return citations

    def _fetch_citing_works(
        self, pub: Publication, citations: list[Citation], author: AuthorProfile,
        seen_edges: set[tuple[str, str]] | None = None,
    ) -> None:
        """Fetch works that cite a given publication (for cited_by_timestamps)."""
        cursor = "*"
        per_page = 200

        while cursor:
            params = self._params({
                "filter": f"cites:{pub.work_id}",
                "per_page": str(per_page),
                "cursor": cursor,
                "select": "id,publication_date,authorships",
            })
            try:
                data = self._http.get(f"{BASE_URL}/works", params=params, source_api="openalex")
            except Exception:
                logger.warning("Failed to fetch citing works for %s", pub.work_id, exc_info=True)
                break

            for citing_work in data.get("results", []):
                citing_id = citing_work.get("id", "").replace("https://openalex.org/", "")
                if not citing_id:
                    continue

                cite_date = None
                date_str = citing_work.get("publication_date")
                if date_str:
                    with contextlib.suppress(ValueError):
                        cite_date = date.fromisoformat(date_str)

                # Deduplicate edges
                edge_key = (citing_id, pub.work_id)
                if seen_edges is not None and edge_key in seen_edges:
                    continue
                if seen_edges is not None:
                    seen_edges.add(edge_key)

                # Check if this is a self-citation (any of citing work's authors is our author)
                is_self = self._is_self_citation(citing_work, author)

                citations.append(
                    Citation(
                        source_work_id=citing_id,
                        target_work_id=pub.work_id,
                        citation_date=cite_date,
                        is_self_citation=is_self,
                        source_api="openalex",
                    )
                )

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")
            if not data.get("results"):
                break

    @staticmethod
    def _is_self_citation(citing_work: dict, author: AuthorProfile) -> bool:
        """Check if a citing work is a self-citation."""
        for authorship in citing_work.get("authorships", []):
            author_obj = authorship.get("author", {})
            citing_author_id = author_obj.get("id", "").replace("https://openalex.org/", "")
            if citing_author_id and citing_author_id == author.openalex_id:
                return True
        return False
