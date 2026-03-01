"""Minimum requirements check for analysis eligibility."""

from __future__ import annotations

from cfd.config.settings import Settings
from cfd.data.models import AuthorProfile


def check_eligibility(profile: AuthorProfile, settings: Settings) -> tuple[bool, str]:
    """Check if author meets minimum requirements for analysis.

    Returns (is_eligible, reason_if_not).
    """
    reasons = []

    if (profile.publication_count or 0) < settings.min_publications:
        reasons.append(f"publications ({profile.publication_count or 0}) < {settings.min_publications}")

    if (profile.citation_count or 0) < settings.min_citations:
        reasons.append(f"citations ({profile.citation_count or 0}) < {settings.min_citations}")

    if (profile.h_index or 0) < settings.min_h_index:
        reasons.append(f"h-index ({profile.h_index or 0}) < {settings.min_h_index}")

    if reasons:
        return False, "Insufficient data: " + "; ".join(reasons)
    return True, ""
