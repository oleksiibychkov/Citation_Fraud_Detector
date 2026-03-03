"""Pydantic domain models for CFD data layer."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class AuthorProfile(BaseModel):
    """Author profile data collected from a scientometric API."""

    scopus_id: str | None = None
    orcid: str | None = None
    openalex_id: str | None = None
    surname: str
    full_name: str | None = None
    display_name_variants: list[str] = Field(default_factory=list)
    institution: str | None = None
    discipline: str | None = None
    h_index: int | None = None
    publication_count: int | None = None
    citation_count: int | None = None
    source_api: str
    raw_data: dict | None = None


class Publication(BaseModel):
    """Publication metadata."""

    work_id: str
    doi: str | None = None
    title: str | None = None
    abstract: str | None = None
    publication_date: date | None = None
    journal: str | None = None
    citation_count: int = 0
    references_list: list[str] = Field(default_factory=list)
    cited_by_works: list[str] = Field(default_factory=list)
    co_authors: list[dict] = Field(default_factory=list)
    source_api: str
    raw_data: dict | None = None


class Citation(BaseModel):
    """A citation relationship between two works."""

    source_work_id: str  # the citing work
    target_work_id: str  # the cited work
    source_author_id: str | None = None
    target_author_id: str | None = None
    source_institution: str | None = None  # institution of citing author
    citation_date: date | None = None
    is_self_citation: bool = False
    source_api: str


class AuthorData(BaseModel):
    """Complete collected data for one author."""

    profile: AuthorProfile
    publications: list[Publication] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    cited_by_timestamps: dict[str, list[date]] = Field(default_factory=dict)
