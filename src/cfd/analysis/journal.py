"""Journal Self-Citation Rate (JSCR) indicator (§3.7)."""

from __future__ import annotations

import logging
from collections import Counter

from cfd.data.models import AuthorData
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def compute_jscr(author_data: AuthorData) -> IndicatorResult:
    """Journal Self-Citation Rate: fraction of references that cite the same journal.

    For each publication, count how many of its references point to papers
    published in the same journal. Aggregate across all publications.

    JSCR = total_same_journal_refs / total_refs
    """
    # Build a lookup: work_id → journal name
    journal_by_work = {}
    for pub in author_data.publications:
        if pub.journal:
            journal_by_work[pub.work_id] = pub.journal.strip().lower()

    total_refs = 0
    same_journal_refs = 0
    per_journal_counts: Counter[str] = Counter()

    for pub in author_data.publications:
        pub_journal = (pub.journal or "").strip().lower()
        if not pub_journal:
            continue

        for ref_id in pub.references_list:
            total_refs += 1
            ref_journal = journal_by_work.get(ref_id)
            if ref_journal and ref_journal == pub_journal:
                same_journal_refs += 1
                per_journal_counts[pub_journal] += 1

    if total_refs == 0:
        return IndicatorResult(
            indicator_type="JSCR",
            value=0.0,
            details={"status": "no_references", "total_refs": 0},
        )

    value = same_journal_refs / total_refs

    # Top journals by same-journal citation count
    top_journals = per_journal_counts.most_common(5)

    return IndicatorResult(
        indicator_type="JSCR",
        value=round(value, 4),
        details={
            "same_journal_refs": same_journal_refs,
            "total_refs": total_refs,
            "top_journals": [{"journal": j, "count": c} for j, c in top_journals],
        },
    )
