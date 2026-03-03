"""Fraud Score aggregation and confidence level classification."""

from __future__ import annotations

from cfd.config.settings import Settings
from cfd.graph.metrics import IndicatorResult

# Full weights for 22 indicators (backward-compatible: score = weighted avg of available)
DEFAULT_WEIGHTS: dict[str, float] = {
    "SCR": 0.07,
    "MCR": 0.09,
    "CB": 0.05,
    "TA": 0.08,
    "HTA": 0.05,
    "RLA": 0.04,
    "GIC": 0.04,
    "EIGEN": 0.03,
    "BETWEENNESS": 0.03,
    "PAGERANK": 0.04,
    "COMMUNITY": 0.03,
    "CLIQUE": 0.03,
    "CV": 0.05,
    "SBD": 0.04,
    "CTX": 0.04,
    "ANA": 0.05,
    "PB": 0.04,
    "SSD": 0.05,
    "CC": 0.04,
    "CPC": 0.03,
    "JSCR": 0.04,
    "COERCE": 0.04,
}

CONFIDENCE_LEVELS: list[tuple[float, float, str]] = [
    (0.0, 0.2, "normal"),
    (0.2, 0.4, "low"),
    (0.4, 0.6, "moderate"),
    (0.6, 0.8, "high"),
    (0.8, 1.01, "critical"),
]


def _normalize_with_cap(value: float, cap: float) -> float:
    """Normalize value to [0, 1] given a cap threshold. Guards against zero cap."""
    if value <= 0:
        return 0.0
    if cap <= 0 or value >= cap:
        return 1.0
    return value / cap


def _normalize_indicator(indicator: IndicatorResult, settings: Settings) -> float:
    """Normalize an indicator value to [0, 1] range based on thresholds."""
    itype = indicator.indicator_type
    value = indicator.value

    if itype == "SCR":
        # 0 at 0, 0.5 at warn threshold, 1.0 at high threshold
        if value <= 0:
            return 0.0
        if value >= settings.scr_high_threshold:
            return 1.0
        delta = settings.scr_high_threshold - settings.scr_warn_threshold
        if value >= settings.scr_warn_threshold:
            return 0.5 + 0.5 * (value - settings.scr_warn_threshold) / delta if delta > 0 else 1.0
        return 0.5 * value / settings.scr_warn_threshold if settings.scr_warn_threshold > 0 else 1.0

    if itype == "MCR":
        return _normalize_with_cap(value, settings.mcr_threshold * 2)

    if itype == "CB":
        return _normalize_with_cap(value, settings.cb_threshold * 2)

    if itype == "RLA":
        return _normalize_with_cap(value, settings.rla_threshold * 2)

    if itype == "GIC":
        return _normalize_with_cap(value, settings.gic_threshold * 1.5)

    if itype == "EIGEN":
        return _normalize_with_cap(value, settings.eigenvector_threshold * 2)

    if itype == "BETWEENNESS":
        return _normalize_with_cap(value, settings.betweenness_threshold * 2)

    if itype == "PAGERANK":
        return _normalize_with_cap(value, settings.pagerank_threshold * 2)

    # TA, HTA, COMMUNITY, CLIQUE, CV, SBD, CTX, ANA, PB, SSD, CC, CPC, JSCR, COERCE are already [0, 1]
    return min(max(value, 0.0), 1.0)


def _is_triggered(indicator: IndicatorResult, settings: Settings) -> bool:
    """Check if an indicator exceeds its threshold."""
    itype = indicator.indicator_type
    value = indicator.value

    if itype == "SCR":
        return value >= settings.scr_warn_threshold
    if itype == "MCR":
        return value > settings.mcr_threshold
    if itype == "CB":
        return value > settings.cb_threshold
    if itype == "TA":
        # Triggered if max z-score >= threshold
        max_z = indicator.details.get("max_z_score", 0)
        return max_z >= settings.ta_z_threshold
    if itype == "HTA":
        max_z = indicator.details.get("max_z_score", 0)
        return max_z >= settings.ta_z_threshold
    if itype == "RLA":
        return value > settings.rla_threshold
    if itype == "GIC":
        return value > settings.gic_threshold
    if itype == "EIGEN":
        return value > settings.eigenvector_threshold
    if itype == "BETWEENNESS":
        return value > settings.betweenness_threshold
    if itype == "PAGERANK":
        return value > settings.pagerank_threshold
    if itype == "COMMUNITY":
        return value > 0.5
    if itype == "CLIQUE":
        return value > 0.5
    if itype == "CV":
        return value > 0.4
    if itype == "SBD":
        return value > settings.sbd_suspicious_threshold
    if itype == "CTX":
        return value > 0.4
    if itype == "ANA":
        return value > 0.4
    if itype == "PB":
        return value > 0.3
    if itype == "SSD":
        return value > 0.3
    if itype == "CC":
        return value > 0.3
    if itype == "CPC":
        return value > 0.3
    if itype == "JSCR":
        return value > 0.3
    if itype == "COERCE":
        return value > 0.3

    return False


def get_trigger_threshold(indicator_type: str, settings: Settings) -> float:
    """Return the trigger threshold for an indicator type."""
    thresholds = {
        "SCR": settings.scr_warn_threshold,
        "MCR": settings.mcr_threshold,
        "CB": settings.cb_threshold,
        "TA": settings.ta_z_threshold,
        "HTA": settings.ta_z_threshold,
        "RLA": settings.rla_threshold,
        "GIC": settings.gic_threshold,
        "EIGEN": settings.eigenvector_threshold,
        "BETWEENNESS": settings.betweenness_threshold,
        "PAGERANK": settings.pagerank_threshold,
        "COMMUNITY": 0.5,
        "CLIQUE": 0.5,
        "CV": 0.4,
        "SBD": settings.sbd_suspicious_threshold,
        "CTX": 0.4,
        "ANA": 0.4,
        "PB": 0.3,
        "SSD": 0.3,
        "CC": 0.3,
        "CPC": 0.3,
        "JSCR": 0.3,
        "COERCE": 0.3,
    }
    return thresholds.get(indicator_type, 0.5)


def compute_fraud_score(
    indicators: list[IndicatorResult],
    settings: Settings,
) -> tuple[float, str, list[str]]:
    """Compute weighted Fraud Score from indicator results.

    Returns (score, confidence_level, triggered_indicators).
    """
    weights = DEFAULT_WEIGHTS
    weighted_sum = 0.0
    total_weight = 0.0
    triggered = []

    for ind in indicators:
        if ind.indicator_type in weights:
            w = weights[ind.indicator_type]
            normalized = _normalize_indicator(ind, settings)
            weighted_sum += w * normalized
            total_weight += w
            if _is_triggered(ind, settings):
                triggered.append(ind.indicator_type)

    score = weighted_sum / total_weight if total_weight > 0 else 0.0
    score = min(max(score, 0.0), 1.0)

    # Determine confidence level
    confidence = "normal"
    for low, high, level in CONFIDENCE_LEVELS:
        if low <= score < high:
            confidence = level
            break

    return round(score, 4), confidence, triggered
