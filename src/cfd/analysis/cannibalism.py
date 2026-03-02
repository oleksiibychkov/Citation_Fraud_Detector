"""Citation Cannibalism (CC) indicator."""

from __future__ import annotations

import logging

from cfd.data.models import AuthorData, Publication
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def compute_cc(
    author_data: AuthorData,
    per_paper_threshold: float = 0.50,
) -> IndicatorResult:
    """Citation Cannibalism: detect excessive self-citation in references.

    CC(paper) = self_citations_in_references / total_references.
    Aggregate: fraction of papers where CC(paper) > threshold.

    Returns IndicatorResult("CC", value, details).
    """
    author_work_ids = {pub.work_id for pub in author_data.publications}

    per_paper = []
    flagged = 0

    for pub in author_data.publications:
        cc_val = _per_paper_cc(pub, author_work_ids)
        if cc_val is None:
            continue
        per_paper.append({"work_id": pub.work_id, "cc": cc_val})
        if cc_val > per_paper_threshold:
            flagged += 1

    total_evaluated = len(per_paper)
    if total_evaluated == 0:
        return IndicatorResult(
            indicator_type="CC",
            value=0.0,
            details={"status": "no_references", "total_evaluated": 0},
        )

    cc_values = [p["cc"] for p in per_paper]
    mean_cc = sum(cc_values) / len(cc_values)
    max_cc = max(cc_values)

    # Normalize: fraction of flagged papers, capped [0, 1]
    value = min(max(flagged / total_evaluated, 0.0), 1.0)

    return IndicatorResult(
        indicator_type="CC",
        value=value,
        details={
            "mean_cc": round(mean_cc, 4),
            "max_cc": round(max_cc, 4),
            "flagged_count": flagged,
            "total_evaluated": total_evaluated,
            "per_paper_threshold": per_paper_threshold,
            "top_papers": sorted(per_paper, key=lambda p: p["cc"], reverse=True)[:5],
        },
    )


def _per_paper_cc(publication: Publication, author_work_ids: set[str]) -> float | None:
    """Compute CC for a single paper. Returns None if no references."""
    if not publication.references_list:
        return None
    self_refs = sum(1 for ref in publication.references_list if ref in author_work_ids)
    return self_refs / len(publication.references_list)
