"""Incremental update logic for repeat analysis."""

from __future__ import annotations

from cfd.db.repositories.authors import AuthorRepository
from cfd.db.repositories.publications import PublicationRepository


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
