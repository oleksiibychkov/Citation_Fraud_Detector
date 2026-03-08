"""Journal analysis pipeline: collect -> indicators -> score."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from cfd.analysis.journal_indicators import (
    compute_j_cb,
    compute_j_cdf,
    compute_j_coerce,
    compute_j_ec,
    compute_j_growth,
    compute_j_hia,
    compute_j_mcr,
    compute_j_scr,
    compute_j_ta,
)
from cfd.data.http_client import CachedHttpClient
from cfd.data.journal_models import JournalData, JournalProfile
from cfd.data.journal_openalex import JournalOpenAlexCollector
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)

# Weights for journal indicators
JOURNAL_WEIGHTS: dict[str, float] = {
    "J_SCR": 0.18,
    "J_MCR": 0.12,
    "J_TA": 0.10,
    "J_HIA": 0.10,
    "J_CDF": 0.12,
    "J_COERCE": 0.12,
    "J_EC": 0.10,
    "J_CB": 0.08,
    "J_GROWTH": 0.08,
}

JOURNAL_CONFIDENCE_LEVELS: list[tuple[float, float, str]] = [
    (0.0, 0.2, "normal"),
    (0.2, 0.4, "low"),
    (0.4, 0.6, "moderate"),
    (0.6, 0.8, "high"),
    (0.8, 1.01, "critical"),
]

# Trigger thresholds for journal indicators
JOURNAL_THRESHOLDS: dict[str, float] = {
    "J_SCR": 0.25,
    "J_MCR": 0.30,
    "J_TA": 0.40,
    "J_HIA": 0.30,
    "J_CDF": 0.30,
    "J_COERCE": 0.30,
    "J_EC": 0.35,
    "J_CB": 0.35,
    "J_GROWTH": 0.40,
}

ZERO_EXCLUSION_EPSILON = 0.01


@dataclass
class JournalAnalysisResult:
    """Complete result of a journal analysis."""

    profile: JournalProfile
    indicators: list[IndicatorResult] = field(default_factory=list)
    fraud_score: float = 0.0
    confidence_level: str = "normal"
    triggered_indicators: list[str] = field(default_factory=list)
    status: str = "completed"
    warnings: list[str] = field(default_factory=list)


def analyze_journal(
    journal_query: str,
    *,
    issn: str | None = None,
    http_client: CachedHttpClient | None = None,
) -> JournalAnalysisResult:
    """Run full journal analysis pipeline."""
    warnings: list[str] = []

    # Step 1: Collect data
    if http_client is None:
        from cfd.config.settings import Settings
        from cfd.data.http_client import RateLimiter
        settings = Settings()
        http_client = CachedHttpClient(
            rate_limiter=RateLimiter(settings.openalex_requests_per_second),
            max_retries=settings.max_retries,
        )

    collector = JournalOpenAlexCollector(http_client)
    journal_data = collector.collect(journal_query, issn=issn)

    if not journal_data.works:
        return JournalAnalysisResult(
            profile=journal_data.profile,
            status="insufficient_data",
            warnings=["No works found for this journal"],
        )

    # Step 2: Compute indicators
    indicators: list[IndicatorResult] = []

    indicator_funcs = [
        ("J_SCR", compute_j_scr),
        ("J_MCR", compute_j_mcr),
        ("J_TA", compute_j_ta),
        ("J_HIA", compute_j_hia),
        ("J_CDF", compute_j_cdf),
        ("J_COERCE", compute_j_coerce),
        ("J_EC", compute_j_ec),
        ("J_CB", compute_j_cb),
        ("J_GROWTH", compute_j_growth),
    ]

    for name, func in indicator_funcs:
        try:
            indicators.append(func(journal_data))
        except Exception:
            logger.warning("%s computation failed", name, exc_info=True)
            warnings.append(f"{name} computation failed")

    # Step 3: Score
    score, confidence, triggered = compute_journal_score(indicators)

    return JournalAnalysisResult(
        profile=journal_data.profile,
        indicators=indicators,
        fraud_score=score,
        confidence_level=confidence,
        triggered_indicators=triggered,
        status="completed",
        warnings=warnings,
    )


def compute_journal_score(
    indicators: list[IndicatorResult],
) -> tuple[float, str, list[str]]:
    """Compute weighted journal fraud score."""
    weighted_sum = 0.0
    total_weight = 0.0
    triggered = []

    for ind in indicators:
        w = JOURNAL_WEIGHTS.get(ind.indicator_type, 0)
        if w == 0:
            continue

        threshold = JOURNAL_THRESHOLDS.get(ind.indicator_type, 0.3)
        if ind.value >= threshold:
            triggered.append(ind.indicator_type)

        if ind.value >= ZERO_EXCLUSION_EPSILON:
            normalized = min(max(ind.value, 0.0), 1.0)
            weighted_sum += w * normalized
            total_weight += w

    score = weighted_sum / total_weight if total_weight > 0 else 0.0
    score = min(max(score, 0.0), 1.0)

    # Tier elevation: if J_SCR + J_COERCE both triggered -> min "moderate"
    if "J_SCR" in triggered and "J_COERCE" in triggered:
        score = max(score, 0.4)
    # If 4+ indicators triggered -> min "high"
    if len(triggered) >= 4:
        score = max(score, 0.6)

    confidence = "normal"
    for low, high, level in JOURNAL_CONFIDENCE_LEVELS:
        if low <= score < high:
            confidence = level
            break

    return round(score, 4), confidence, triggered


def get_journal_trigger_threshold(indicator_type: str) -> float:
    """Return the trigger threshold for a journal indicator."""
    return JOURNAL_THRESHOLDS.get(indicator_type, 0.3)
