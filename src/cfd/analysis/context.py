"""Contextual Anomaly Analysis (CTX) — 4-step verification."""

from __future__ import annotations

import logging

from cfd.data.models import AuthorData
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def contextual_check(
    author_data: AuthorData,
    indicator_results: dict[str, IndicatorResult],
    independent_threshold: int = 3,
) -> IndicatorResult:
    """Contextual Anomaly Analysis: 4-step verification.

    Step 1 — Trigger: TA, HTA, or CB above threshold
    Step 2 — Context: review article detection, publication spike correlation
    Step 3 — Structure: citation bottleneck in spike window, self-citation surge, clique overlap
    Step 4 — Aggregation: count independent signals, >=3 = high CTX

    Args:
        author_data: Complete author data.
        indicator_results: Already-computed indicator results keyed by type.
        independent_threshold: Number of independent signals needed for high CTX.

    Returns:
        IndicatorResult with CTX score and evidence details.
    """
    signals: list[dict] = []
    mitigations: list[str] = []

    # ---- Step 1: Trigger check ----
    ta = indicator_results.get("TA")
    hta = indicator_results.get("HTA")
    cb = indicator_results.get("CB")

    triggered = False
    trigger_reasons = []

    if ta and ta.value > 0.4:
        triggered = True
        trigger_reasons.append(f"TA={ta.value:.3f}")
    if hta and hta.value > 0.4:
        triggered = True
        trigger_reasons.append(f"HTA={hta.value:.3f}")
    if cb and cb.value > 0.3:
        triggered = True
        trigger_reasons.append(f"CB={cb.value:.3f}")

    if not triggered:
        return IndicatorResult(
            "CTX",
            0.0,
            {"status": "not_triggered", "reason": "no_indicators_above_threshold"},
        )

    # ---- Step 2: Context signals ----
    # 2a. Review article detection
    review_count = _count_review_articles(author_data)
    total_pubs = len(author_data.publications)
    if total_pubs > 0:
        review_ratio = review_count / total_pubs
        if review_ratio > 0.3:
            mitigations.append(f"high_review_ratio={review_ratio:.2f}")
        elif review_ratio > 0.0:
            pass  # some reviews are normal
    else:
        review_ratio = 0.0

    # 2b. Publication spike correlation (TA already computes this)
    pub_corr = None
    if ta and ta.details.get("citation_pub_correlation") is not None:
        pub_corr = ta.details["citation_pub_correlation"]
        if pub_corr < 0.3:
            signals.append({
                "type": "low_citation_pub_correlation",
                "value": pub_corr,
                "description": "Citation spike uncorrelated with publication activity",
            })
        elif pub_corr > 0.7:
            mitigations.append(f"citation_pub_correlated={pub_corr:.2f}")

    # ---- Step 3: Structural signals ----
    # 3a. Citation bottleneck severity
    if cb and cb.value > 0.5:
        signals.append({
            "type": "high_citation_bottleneck",
            "value": cb.value,
            "description": "Citations dominated by a single source",
        })

    # 3b. Self-citation surge
    scr = indicator_results.get("SCR")
    if scr and scr.value > 0.3:
        signals.append({
            "type": "high_self_citation",
            "value": scr.value,
            "description": "Self-citation ratio exceeds discipline norms",
        })

    # 3c. Clique overlap
    clique = indicator_results.get("CLIQUE")
    if clique and clique.value > 0.3:
        signals.append({
            "type": "clique_involvement",
            "value": clique.value,
            "description": "Author involved in citation clique",
        })

    # 3d. Community anomaly
    community = indicator_results.get("COMMUNITY")
    if community and community.value > 0.3:
        signals.append({
            "type": "suspicious_community",
            "value": community.value,
            "description": "Author in dense citation community",
        })

    # 3e. Mutual citation excess
    mcr = indicator_results.get("MCR")
    if mcr and mcr.value > 0.3:
        signals.append({
            "type": "high_mutual_citation",
            "value": mcr.value,
            "description": "Excessive mutual citation with a co-author",
        })

    # 3f. Citation velocity anomaly
    cv = indicator_results.get("CV")
    if cv and cv.value > 0.4:
        signals.append({
            "type": "high_citation_velocity",
            "value": cv.value,
            "description": "Papers accumulating citations abnormally fast",
        })

    # 3g. Sleeping beauty suspicion
    sbd = indicator_results.get("SBD")
    if sbd and sbd.value > 0.3:
        signals.append({
            "type": "sleeping_beauty_pattern",
            "value": sbd.value,
            "description": "Papers with suspicious delayed citation patterns",
        })

    # 3h. Salami slicing suspicion
    ssd = indicator_results.get("SSD")
    if ssd and ssd.value > 0.3:
        signals.append({
            "type": "salami_slicing",
            "value": ssd.value,
            "description": "Suspiciously similar publications detected",
        })

    # 3i. Citation cannibalism
    cc = indicator_results.get("CC")
    if cc and cc.value > 0.3:
        signals.append({
            "type": "citation_cannibalism",
            "value": cc.value,
            "description": "Excessive self-referencing in publication references",
        })

    # 3j. Authorship network anomaly
    ana = indicator_results.get("ANA")
    if ana and ana.value > 0.4:
        signals.append({
            "type": "authorship_anomaly",
            "value": ana.value,
            "description": "Anomalous co-authorship patterns detected",
        })

    # 3k. Cross-platform consistency
    cpc = indicator_results.get("CPC")
    if cpc and cpc.value > 0.3:
        signals.append({
            "type": "cross_platform_inconsistency",
            "value": cpc.value,
            "description": "Significant metric divergence across platforms",
        })

    # 3l. View count check (stubbed — data not available)
    # In a real system, compare citation counts with view/download counts
    # to detect citations without corresponding readership
    view_check = {"status": "unavailable", "reason": "view_data_not_available"}

    # ---- Step 4: Aggregation ----
    independent_signal_count = len(signals)

    # Apply mitigations (reduce score if legitimate explanations exist)
    mitigation_factor = max(0.5, 1.0 - 0.15 * len(mitigations))

    # Normalize: independent_threshold -> 0.5, threshold*2 -> 1.0
    raw_score = independent_signal_count / (independent_threshold * 2) if independent_threshold > 0 else 0.0
    adjusted_score = raw_score * mitigation_factor
    normalized = min(max(adjusted_score, 0.0), 1.0)

    return IndicatorResult(
        "CTX",
        normalized,
        {
            "trigger_reasons": trigger_reasons,
            "signals": signals,
            "signal_count": independent_signal_count,
            "independent_threshold": independent_threshold,
            "mitigations": mitigations,
            "mitigation_factor": round(mitigation_factor, 3),
            "review_article_ratio": round(review_ratio, 3),
            "view_check": view_check,
        },
    )


def _count_review_articles(author_data: AuthorData) -> int:
    """Count publications that are likely review articles (heuristic)."""
    count = 0
    for pub in author_data.publications:
        if not pub.title:
            continue
        title_lower = pub.title.lower()
        # Heuristic: review articles often have these patterns in titles
        if any(kw in title_lower for kw in ("review", "survey", "meta-analysis", "systematic review", "overview")):
            count += 1
        # Also check raw_data for type field
        if pub.raw_data and pub.raw_data.get("type") in ("review", "review-article"):
            count += 1
            continue
    return count
