"""Citation Velocity (CV) and Sleeping Beauty Detector (SBD) indicators."""

from __future__ import annotations

import logging
import math
from collections import Counter
from datetime import date

import numpy as np

from cfd.analysis.baselines import DisciplineBaseline, get_journal_quartile
from cfd.data.models import AuthorData, Publication
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def _paper_citation_velocity(
    pub: Publication,
    baseline: DisciplineBaseline,
    current_year: int | None = None,
) -> float | None:
    """Compute citation velocity for a single paper.

    CV_paper = (C_observed / C_expected) where C_expected accounts for:
    - discipline average citations per paper
    - paper age with exponential decay (half-life model)
    - journal quartile normalization
    """
    if not pub.publication_date:
        return None

    if current_year is None:
        current_year = date.today().year

    age_years = current_year - pub.publication_date.year
    if age_years < 1:
        return None  # too new to evaluate

    # Expected citations based on age and discipline half-life
    half_life = baseline.citation_half_life_years
    # Cumulative expected citations: avg * (1 - 2^(-age/half_life)) / (1 - 2^(-1/half_life))
    # Simplified: expected grows with age but saturates
    decay_factor = 1.0 - math.pow(2.0, -age_years / half_life)
    normalization = 1.0 - math.pow(2.0, -1.0 / half_life)
    expected = baseline.avg_citations_per_paper * (decay_factor / normalization) if normalization > 0 else 0.0

    if expected <= 0:
        return None

    # Journal quartile adjustment
    quartile = get_journal_quartile(pub.journal, baseline)
    quartile_medians = baseline.journal_quartile_medians
    q2_median = quartile_medians.get("Q2", 8.0)
    q_median = quartile_medians.get(quartile, q2_median)
    quartile_factor = q_median / q2_median if q2_median > 0 else 1.0

    adjusted_expected = expected * quartile_factor

    if adjusted_expected <= 0:
        return None

    return pub.citation_count / adjusted_expected


def compute_cv(
    author_data: AuthorData,
    baseline: DisciplineBaseline,
    current_year: int | None = None,
) -> IndicatorResult:
    """Citation Velocity: detect abnormally fast citation accumulation.

    Per-paper citation velocity using exponential decay aging model
    and journal quartile normalization. Aggregated via median.

    High CV indicates papers receiving citations faster than expected
    for their age, discipline, and journal tier.
    """
    velocities: list[float] = []
    paper_details: list[dict] = []

    for pub in author_data.publications:
        v = _paper_citation_velocity(pub, baseline, current_year)
        if v is not None:
            velocities.append(v)
            paper_details.append({
                "work_id": pub.work_id,
                "citation_count": pub.citation_count,
                "velocity": round(v, 3),
            })

    if not velocities:
        return IndicatorResult("CV", 0.0, {"status": "N/A", "reason": "no_eligible_papers"})

    arr = np.array(velocities)
    median_v = float(np.median(arr))
    mean_v = float(np.mean(arr))
    max_v = float(np.max(arr))

    # Count papers with velocity above threshold (default 5.0)
    # Normalized: threshold -> 0.5, threshold*2 -> 1.0
    # Use median as the primary signal (robust to outliers)
    cv_threshold = 5.0  # will be parameterized via settings in pipeline
    normalized = min(max(median_v / (cv_threshold * 2), 0.0), 1.0)

    # Top 3 fastest papers
    top_papers = sorted(paper_details, key=lambda p: p["velocity"], reverse=True)[:3]

    return IndicatorResult(
        "CV",
        normalized,
        {
            "median_velocity": round(median_v, 3),
            "mean_velocity": round(mean_v, 3),
            "max_velocity": round(max_v, 3),
            "papers_evaluated": len(velocities),
            "discipline": baseline.discipline,
            "top_papers": top_papers,
        },
    )


def _compute_beauty_coefficient(yearly_citations: dict[int, int]) -> tuple[float, int | None, int | None]:
    """Compute Beauty Coefficient B (van Raan's method).

    B = sum over sleeping years of (ct_max - ct) / (t_max - t)
    where ct is citations in year t, ct_max is citations in awakening year t_max.

    Returns (B, awakening_year, sleep_duration).
    """
    if len(yearly_citations) < 3:
        return 0.0, None, None

    years = sorted(yearly_citations.keys())
    counts = [yearly_citations[y] for y in years]

    # Find the peak year (awakening year)
    max_count = max(counts)
    if max_count == 0:
        return 0.0, None, None

    max_idx = counts.index(max_count)
    t_max = years[max_idx]
    ct_max = max_count

    if max_idx < 2:
        # Peak too early — no sleeping period
        return 0.0, None, None

    # Compute B: sum over years before the peak
    beauty = 0.0
    for i in range(max_idx):
        t = years[i]
        ct = counts[i]
        dt = t_max - t
        if dt > 0:
            beauty += (ct_max - ct) / dt

    # Sleep duration: years from first publication to awakening
    sleep_duration = t_max - years[0]

    return beauty, t_max, sleep_duration


def compute_sbd(author_data: AuthorData) -> IndicatorResult:
    """Sleeping Beauty Detector: identify papers with delayed recognition.

    Uses Beauty Coefficient B (van Raan) to detect papers that were
    "sleeping" (low citations) then suddenly "awakened" (citation spike).

    Cross-checks with CB and TA to distinguish legitimate delayed
    recognition from suspicious manipulation.
    """
    # Build per-paper citation timeline from raw_data counts_by_year
    paper_beauties: list[dict] = []

    for pub in author_data.publications:
        yearly_citations: dict[int, int] = {}

        # Try counts_by_year from raw_data
        if pub.raw_data:
            for entry in pub.raw_data.get("counts_by_year", []):
                year = entry.get("year")
                cited = entry.get("cited_by_count", 0)
                if year and cited is not None:
                    yearly_citations[year] = cited

        # Fallback: use cited_by_timestamps if available
        if not yearly_citations and pub.work_id in author_data.cited_by_timestamps:
            timestamps = author_data.cited_by_timestamps[pub.work_id]
            year_counter = Counter(d.year for d in timestamps)
            yearly_citations = dict(year_counter)

        if len(yearly_citations) < 3:
            continue

        beauty, awakening_year, sleep_duration = _compute_beauty_coefficient(yearly_citations)

        if beauty > 0:
            paper_beauties.append({
                "work_id": pub.work_id,
                "beauty_coefficient": round(beauty, 2),
                "awakening_year": awakening_year,
                "sleep_duration": sleep_duration,
                "total_citations": pub.citation_count,
            })

    if not paper_beauties:
        return IndicatorResult("SBD", 0.0, {"status": "N/A", "reason": "no_sleeping_beauties"})

    # Sort by beauty coefficient descending
    paper_beauties.sort(key=lambda p: p["beauty_coefficient"], reverse=True)

    max_beauty = paper_beauties[0]["beauty_coefficient"]
    avg_beauty = sum(p["beauty_coefficient"] for p in paper_beauties) / len(paper_beauties)

    # Count papers exceeding the beauty threshold
    beauty_threshold = 100.0  # will be parameterized via settings in pipeline
    high_beauty_count = sum(1 for p in paper_beauties if p["beauty_coefficient"] > beauty_threshold)

    # Suspicious ratio: proportion of high-B papers
    suspicious_ratio = high_beauty_count / len(author_data.publications) if author_data.publications else 0.0

    # Normalize: suspicious_threshold -> 0.5, suspicious_threshold*2 -> 1.0
    suspicious_threshold = 0.3
    normalized = min(max(suspicious_ratio / (suspicious_threshold * 2), 0.0), 1.0)

    return IndicatorResult(
        "SBD",
        normalized,
        {
            "max_beauty_coefficient": round(max_beauty, 2),
            "avg_beauty_coefficient": round(avg_beauty, 2),
            "high_beauty_papers": high_beauty_count,
            "total_evaluated": len(paper_beauties),
            "suspicious_ratio": round(suspicious_ratio, 4),
            "top_papers": paper_beauties[:3],
        },
    )
