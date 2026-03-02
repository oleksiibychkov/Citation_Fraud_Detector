"""Incremental update logic for repeat analysis."""

from __future__ import annotations

import logging

from cfd.db.repositories.authors import AuthorRepository
from cfd.db.repositories.publications import PublicationRepository

logger = logging.getLogger(__name__)


def check_what_changed(
    author_id: int,
    author_repo: AuthorRepository,
    pub_repo: PublicationRepository,
) -> dict:
    """Compare current stored data to determine if incremental update is needed.

    Returns dict with is_new, last_updated, stored_publication_count, etc.
    """
    stored_author = author_repo.get_by_id(author_id)
    if stored_author is None:
        return {"is_new": True}

    stored_pub_count = pub_repo.get_count_by_author_id(author_id)

    return {
        "is_new": False,
        "last_updated": stored_author.get("updated_at"),
        "stored_publication_count": stored_pub_count,
        "stored_citation_count": stored_author.get("citation_count", 0),
        "stored_h_index": stored_author.get("h_index", 0),
    }


def should_skip_analysis(
    stored: dict,
    current_publication_count: int | None,
    current_citation_count: int | None,
) -> tuple[bool, dict]:
    """Decide whether a re-analysis can be skipped (no meaningful changes).

    Args:
        stored: dict from check_what_changed().
        current_publication_count: fresh publication count from API.
        current_citation_count: fresh citation count from API.

    Returns:
        (skip, delta_info) where skip=True means nothing changed.
    """
    if stored.get("is_new", True):
        return False, {"reason": "new_author"}

    # If API returned None for counts, we can't compare — always re-analyze
    if current_publication_count is None or current_citation_count is None:
        return False, {"reason": "unknown_counts"}

    stored_pubs = stored.get("stored_publication_count", 0) or 0
    stored_cits = stored.get("stored_citation_count", 0) or 0
    current_pubs = current_publication_count
    current_cits = current_citation_count

    pub_delta = current_pubs - stored_pubs
    cit_delta = current_cits - stored_cits

    delta_info = {
        "publication_delta": pub_delta,
        "citation_delta": cit_delta,
        "stored_publication_count": stored_pubs,
        "stored_citation_count": stored_cits,
    }

    # Skip only when both deltas are zero (no new publications, no new citations)
    skip = pub_delta == 0 and cit_delta == 0
    if skip:
        logger.info("No changes detected — skipping re-analysis")

    return skip, delta_info
