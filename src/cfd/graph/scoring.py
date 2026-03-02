"""Fraud Score aggregation and confidence level classification."""

from __future__ import annotations

from cfd.config.settings import Settings
from cfd.graph.metrics import IndicatorResult

# Full weights for 20 indicators (backward-compatible: score = weighted avg of available)
DEFAULT_WEIGHTS: dict[str, float] = {
    "SCR": 0.08,
    "MCR": 0.10,
    "CB": 0.06,
    "TA": 0.08,
    "HTA": 0.06,
    "RLA": 0.05,
    "GIC": 0.05,
    "EIGEN": 0.03,
    "BETWEENNESS": 0.03,
    "PAGERANK": 0.05,
    "COMMUNITY": 0.03,
    "CLIQUE": 0.03,
    "CV": 0.06,
    "SBD": 0.04,
    "CTX": 0.04,
    "ANA": 0.05,
    "PB": 0.04,
    "SSD": 0.05,
    "CC": 0.04,
    "CPC": 0.03,
}

CONFIDENCE_LEVELS: list[tuple[float, float, str]] = [
    (0.0, 0.2, "normal"),
    (0.2, 0.4, "low"),
    (0.4, 0.6, "moderate"),
    (0.6, 0.8, "high"),
    (0.8, 1.01, "critical"),
]


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
        if value >= settings.scr_warn_threshold:
            return 0.5 + 0.5 * (value - settings.scr_warn_threshold) / (
                settings.scr_high_threshold - settings.scr_warn_threshold
            )
        return 0.5 * value / settings.scr_warn_threshold

    if itype == "MCR":
        if value <= 0:
            return 0.0
        if value >= settings.mcr_threshold * 2:
            return 1.0
        return value / (settings.mcr_threshold * 2)

    if itype == "CB":
        if value <= 0:
            return 0.0
        if value >= settings.cb_threshold * 2:
            return 1.0
        return value / (settings.cb_threshold * 2)

    if itype == "RLA":
        if value <= 0:
            return 0.0
        if value >= settings.rla_threshold * 2:
            return 1.0
        return value / (settings.rla_threshold * 2)

    if itype == "GIC":
        if value <= 0:
            return 0.0
        if value >= settings.gic_threshold * 1.5:
            return 1.0
        return value / (settings.gic_threshold * 1.5)

    if itype == "EIGEN":
        if value <= 0:
            return 0.0
        if value >= settings.eigenvector_threshold * 2:
            return 1.0
        return value / (settings.eigenvector_threshold * 2)

    if itype == "BETWEENNESS":
        if value <= 0:
            return 0.0
        if value >= settings.betweenness_threshold * 2:
            return 1.0
        return value / (settings.betweenness_threshold * 2)

    if itype == "PAGERANK":
        if value <= 0:
            return 0.0
        if value >= settings.pagerank_threshold * 2:
            return 1.0
        return value / (settings.pagerank_threshold * 2)

    # TA, HTA, COMMUNITY, CLIQUE, CV, SBD, CTX, ANA, PB, SSD, CC, CPC are already normalized to [0, 1]
    return min(max(value, 0.0), 1.0)


def _is_triggered(indicator: IndicatorResult, settings: Settings) -> bool:
    """Check if an indicator exceeds its threshold."""
    itype = indicator.indicator_type
    value = indicator.value

    if itype == "SCR":
        return value > settings.scr_warn_threshold
    if itype == "MCR":
        return value > settings.mcr_threshold
    if itype == "CB":
        return value > settings.cb_threshold
    if itype == "TA":
        # Triggered if max z-score > threshold
        max_z = indicator.details.get("max_z_score", 0)
        return max_z > settings.ta_z_threshold
    if itype == "HTA":
        max_z = indicator.details.get("max_z_score", 0)
        return max_z > settings.ta_z_threshold
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

    return False


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
