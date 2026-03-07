"""OpenAlex data collection for journal-level analysis."""

from __future__ import annotations

import contextlib
import logging
from collections import Counter
from datetime import date

from cfd.data.http_client import CachedHttpClient
from cfd.data.journal_models import (
    JournalCitation,
    JournalData,
    JournalProfile,
    JournalWork,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org"


class JournalOpenAlexCollector:
    """Collect journal data from OpenAlex /sources and /works endpoints."""

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

    def collect(self, journal_query: str, *, issn: str | None = None) -> JournalData:
        """Collect full journal data: profile, works, citations."""
        profile = self._fetch_journal(journal_query, issn=issn)
        works = self._fetch_works(profile.openalex_id)
        citations, citing_journals = self._analyze_citations(profile.openalex_id, works)

        return JournalData(
            profile=profile,
            works=works,
            citations=citations,
            citing_journals=citing_journals,
        )

    def _fetch_journal(self, query: str, *, issn: str | None = None) -> JournalProfile:
        """Fetch journal profile from OpenAlex /sources."""
        if issn:
            params = self._params({"filter": f"issn:{issn}"})
        else:
            params = self._params({"search": query})

        data = self._http.get(f"{BASE_URL}/sources", params=params, source_api="openalex")
        results = data.get("results", [])
        if not results:
            raise ValueError(f"Journal not found: {query}")

        return self._parse_journal(results[0])

    def _parse_journal(self, data: dict) -> JournalProfile:
        """Parse OpenAlex source response into JournalProfile."""
        openalex_id = (data.get("id") or "").replace("https://openalex.org/", "")
        summary = data.get("summary_stats") or {}

        subjects = []
        for topic in data.get("topics", []):
            name = topic.get("display_name")
            if name:
                subjects.append(name)
        if not subjects:
            for concept in data.get("x_concepts", []):
                name = concept.get("display_name")
                if name:
                    subjects.append(name)

        return JournalProfile(
            openalex_id=openalex_id,
            issn=data.get("issn") or [],
            issn_l=data.get("issn_l"),
            display_name=data.get("display_name") or "",
            publisher=data.get("host_organization_name"),
            country_code=data.get("country_code"),
            type=data.get("type"),
            homepage_url=data.get("homepage_url"),
            works_count=data.get("works_count") or 0,
            cited_by_count=data.get("cited_by_count") or 0,
            h_index=summary.get("h_index"),
            i10_index=summary.get("i10_index"),
            apc_usd=(data.get("apc_usd") or {}).get("price") if isinstance(data.get("apc_usd"), dict) else None,
            is_oa=data.get("is_oa") or False,
            subjects=subjects[:10],
            counts_by_year=data.get("counts_by_year") or [],
            raw_data=data,
        )

    def _fetch_works(self, source_id: str, max_works: int = 500) -> list[JournalWork]:
        """Fetch recent works published in this journal."""
        works = []
        cursor = "*"
        per_page = 200

        while cursor and len(works) < max_works:
            params = self._params({
                "filter": f"primary_location.source.id:{source_id}",
                "per_page": str(per_page),
                "cursor": cursor,
                "sort": "publication_date:desc",
                "select": "id,doi,title,publication_date,cited_by_count,"
                "referenced_works,authorships,counts_by_year",
            })
            data = self._http.get(f"{BASE_URL}/works", params=params, source_api="openalex")

            for work in data.get("results", []):
                parsed = self._parse_work(work, source_id)
                if parsed:
                    works.append(parsed)

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")
            if not data.get("results"):
                break

        logger.info("Fetched %d works for journal %s", len(works), source_id)
        return works

    def _parse_work(self, work: dict, journal_source_id: str) -> JournalWork | None:
        work_id = (work.get("id") or "").replace("https://openalex.org/", "")
        if not work_id:
            return None

        pub_date = None
        date_str = work.get("publication_date")
        if date_str:
            with contextlib.suppress(ValueError):
                pub_date = date.fromisoformat(date_str)

        authors = []
        for authorship in work.get("authorships") or []:
            author_obj = authorship.get("author") or {}
            author_id = (author_obj.get("id") or "").replace("https://openalex.org/", "")
            institutions = authorship.get("institutions") or []
            inst_name = institutions[0].get("display_name") if institutions else None
            authors.append({
                "author_id": author_id,
                "display_name": author_obj.get("display_name") or "",
                "institution": inst_name,
                "position": authorship.get("author_position") or "middle",
            })

        return JournalWork(
            work_id=work_id,
            doi=work.get("doi"),
            title=work.get("title"),
            publication_date=pub_date,
            cited_by_count=work.get("cited_by_count") or 0,
            authors=authors,
            references_list=[
                ref.replace("https://openalex.org/", "")
                for ref in (work.get("referenced_works") or [])
                if ref is not None
            ],
            source_journal_id=journal_source_id,
            raw_data=work,
        )

    def _analyze_citations(
        self, source_id: str, works: list[JournalWork],
    ) -> tuple[list[JournalCitation], dict[str, int]]:
        """Analyze citation patterns: self-citations, citing journals."""
        citations: list[JournalCitation] = []
        citing_journals: Counter[str] = Counter()
        work_ids = {w.work_id for w in works}

        # Sample citing works for the journal's publications
        sampled = works[:100]  # analyze citations for top 100 works
        for work in sampled:
            self._fetch_citing_works_for_journal(
                work, source_id, work_ids, citations, citing_journals,
            )

        return citations, dict(citing_journals)

    def _fetch_citing_works_for_journal(
        self,
        work: JournalWork,
        journal_source_id: str,
        journal_work_ids: set[str],
        citations: list[JournalCitation],
        citing_journals: Counter[str],
    ) -> None:
        """Fetch works that cite a given publication and track journal sources."""
        params = self._params({
            "filter": f"cites:{work.work_id}",
            "per_page": "200",
            "cursor": "*",
            "select": "id,publication_date,primary_location",
        })
        try:
            data = self._http.get(f"{BASE_URL}/works", params=params, source_api="openalex")
        except Exception:
            logger.warning("Failed to fetch citing works for %s", work.work_id, exc_info=True)
            return

        for citing_work in data.get("results") or []:
            citing_id = (citing_work.get("id") or "").replace("https://openalex.org/", "")
            if not citing_id:
                continue

            # Extract citing journal
            location = citing_work.get("primary_location") or {}
            source = location.get("source") or {}
            citing_source_id = (source.get("id") or "").replace("https://openalex.org/", "")

            is_self = citing_source_id == journal_source_id
            if citing_source_id:
                citing_journals[citing_source_id] += 1

            cite_date = None
            date_str = citing_work.get("publication_date")
            if date_str:
                with contextlib.suppress(ValueError):
                    cite_date = date.fromisoformat(date_str)

            citations.append(JournalCitation(
                source_work_id=citing_id,
                target_work_id=work.work_id,
                source_journal_id=citing_source_id or None,
                target_journal_id=journal_source_id,
                citation_date=cite_date,
                is_self_citation=is_self,
            ))
