"""Coercive Citation Detection (COERCE) indicator (§3.7)."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict

from cfd.data.models import AuthorData
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def detect_coercive_citations(
    author_data: AuthorData,
    concentration_threshold: float = 0.25,
    recent_bias_threshold: float = 0.50,
    recent_years: int = 2,
) -> IndicatorResult:
    """Detect potential coercive citation patterns.

    Three signals:
    1. Journal reference concentration: >threshold of all refs cite one journal.
    2. Recent bias: >threshold of same-journal refs cite papers from last N years.
    3. Trend increase: rising same-journal citation ratio over time.

    Final score = weighted combination of triggered signals, ∈ [0, 1].
    """
    # Build work_id → journal lookup
    journal_by_work: dict[str, str] = {}
    for pub in author_data.publications:
        if pub.journal:
            journal_by_work[pub.work_id] = pub.journal.strip().lower()

    # Build work_id → year lookup
    year_by_work: dict[str, int] = {}
    for pub in author_data.publications:
        if pub.publication_date:
            year_by_work[pub.work_id] = pub.publication_date.year

    # Count refs by journal for each publication
    ref_journal_counts: Counter[str] = Counter()
    total_refs = 0
    same_journal_by_year: defaultdict[int, list[bool]] = defaultdict(list)

    for pub in author_data.publications:
        pub_journal = (pub.journal or "").strip().lower()
        pub_year = pub.publication_date.year if pub.publication_date else None

        for ref_id in pub.references_list:
            total_refs += 1
            ref_journal = journal_by_work.get(ref_id)
            if ref_journal:
                ref_journal_counts[ref_journal] += 1
                if pub_year and pub_journal and ref_journal == pub_journal:
                    ref_year = year_by_work.get(ref_id)
                    if ref_year:
                        is_recent = (pub_year - ref_year) <= recent_years
                        same_journal_by_year[pub_year].append(is_recent)

    if total_refs == 0:
        return IndicatorResult(
            indicator_type="COERCE",
            value=0.0,
            details={"status": "no_references", "total_refs": 0},
        )

    # Signal 1: Journal concentration
    top_journal, top_count = ref_journal_counts.most_common(1)[0] if ref_journal_counts else ("", 0)
    concentration = top_count / total_refs if total_refs else 0.0
    signal_concentration = concentration > concentration_threshold

    # Signal 2: Recent bias among same-journal refs
    all_recent_flags = []
    for flags in same_journal_by_year.values():
        all_recent_flags.extend(flags)
    recent_fraction = (
        sum(all_recent_flags) / len(all_recent_flags) if all_recent_flags else 0.0
    )
    signal_recent_bias = recent_fraction > recent_bias_threshold

    # Signal 3: Trend increase — rising ratio over years
    signal_trend = _detect_trend_increase(same_journal_by_year)

    # Combine signals
    signals_triggered = sum([signal_concentration, signal_recent_bias, signal_trend])
    value = min(signals_triggered / 3.0, 1.0)

    return IndicatorResult(
        indicator_type="COERCE",
        value=round(value, 4),
        details={
            "top_journal": top_journal,
            "concentration": round(concentration, 4),
            "concentration_threshold": concentration_threshold,
            "signal_concentration": signal_concentration,
            "recent_fraction": round(recent_fraction, 4),
            "recent_bias_threshold": recent_bias_threshold,
            "signal_recent_bias": signal_recent_bias,
            "signal_trend_increase": signal_trend,
            "signals_triggered": signals_triggered,
            "total_refs": total_refs,
        },
    )


def _detect_trend_increase(
    same_journal_by_year: defaultdict[int, list[bool]],
) -> bool:
    """Check if the fraction of recent same-journal refs is increasing over time."""
    if len(same_journal_by_year) < 2:
        return False

    yearly_ratios = []
    for year in sorted(same_journal_by_year):
        flags = same_journal_by_year[year]
        if flags:
            yearly_ratios.append((year, sum(flags) / len(flags)))

    if len(yearly_ratios) < 2:
        return False

    # Simple check: is the latest ratio higher than the earliest?
    return yearly_ratios[-1][1] > yearly_ratios[0][1]
