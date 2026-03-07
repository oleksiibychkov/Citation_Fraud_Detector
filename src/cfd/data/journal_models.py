"""Pydantic domain models for journal-level analysis."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class JournalProfile(BaseModel):
    """Journal profile data from OpenAlex /sources endpoint."""

    openalex_id: str
    issn: list[str] = Field(default_factory=list)
    issn_l: str | None = None
    display_name: str
    publisher: str | None = None
    country_code: str | None = None
    type: str | None = None  # journal, repository, etc.
    homepage_url: str | None = None
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int | None = None
    i10_index: int | None = None
    apc_usd: int | None = None
    is_oa: bool = False
    subjects: list[str] = Field(default_factory=list)
    counts_by_year: list[dict] = Field(default_factory=list)
    raw_data: dict | None = None


class JournalWork(BaseModel):
    """A work published in the journal, with citation metadata."""

    work_id: str
    doi: str | None = None
    title: str | None = None
    publication_date: date | None = None
    cited_by_count: int = 0
    authors: list[dict] = Field(default_factory=list)
    references_list: list[str] = Field(default_factory=list)
    source_journal_id: str | None = None  # OpenAlex source ID of citing journal
    raw_data: dict | None = None


class JournalCitation(BaseModel):
    """A citation relationship involving the journal."""

    source_work_id: str
    target_work_id: str
    source_journal_id: str | None = None
    target_journal_id: str | None = None
    citation_date: date | None = None
    is_self_citation: bool = False  # same journal


class JournalData(BaseModel):
    """Complete collected data for one journal analysis."""

    profile: JournalProfile
    works: list[JournalWork] = Field(default_factory=list)
    citations: list[JournalCitation] = Field(default_factory=list)
    citing_journals: dict[str, int] = Field(default_factory=dict)  # journal_id -> count
    editorial_board: list[dict] = Field(default_factory=list)
