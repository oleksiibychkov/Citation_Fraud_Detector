"""Evidence collection from analysis results."""

from __future__ import annotations

import logging

from cfd.analysis.pipeline import AnalysisResult
from cfd.data.models import AuthorData

logger = logging.getLogger(__name__)


def collect_evidence(result: AnalysisResult, author_data: AuthorData) -> list[dict]:
    """Transform triggered indicators into evidence records.

    Each evidence record contains the indicator type, value, and a
    human-readable description of why it was flagged.
    """
    evidence = []

    for ind in result.indicators:
        if ind.indicator_type not in result.triggered_indicators:
            continue

        description = _describe_evidence(ind.indicator_type, ind.value, ind.details)
        evidence.append({
            "evidence_type": "indicator",
            "indicator_type": ind.indicator_type,
            "value": round(ind.value, 6),
            "description": description,
            "details": ind.details,
        })

    # Add overall fraud score as evidence
    if result.fraud_score > 0.4:
        evidence.append({
            "evidence_type": "aggregate",
            "indicator_type": "FRAUD_SCORE",
            "value": result.fraud_score,
            "description": f"Overall fraud score {result.fraud_score:.4f} ({result.confidence_level})",
        })

    # Add theorem results as evidence
    for tr in result.theorem_results:
        if tr.passed:
            evidence.append({
                "evidence_type": "theorem",
                "indicator_type": f"T{tr.theorem_number}",
                "value": 1.0,
                "description": f"Theorem {tr.theorem_number} passed: {tr.details}",
            })

    return evidence


def save_evidence(evidence: list[dict], repo, author_id: int, algorithm_version: str) -> None:
    """Persist evidence records to the database."""
    if not evidence or not repo:
        return
    try:
        repo.save_many(author_id, evidence, algorithm_version)
    except Exception:
        logger.warning("Failed to save evidence to DB", exc_info=True)


def _describe_evidence(indicator_type: str, value: float, details: dict) -> str:
    """Generate human-readable description for an evidence record."""
    descriptions = {
        "SCR": f"Self-citation ratio of {value:.2%} exceeds discipline norms",
        "MCR": f"Mutual citation ratio of {value:.4f} suggests citation exchange",
        "CB": f"Citation bottleneck of {value:.2%} — citations dominated by single source",
        "TA": f"Temporal anomaly detected (z-score: {details.get('max_z_score', '?')})",
        "HTA": f"h-index growth anomaly (z-score: {details.get('max_z_score', '?')})",
        "RLA": f"Reference list anomaly score {value:.4f}",
        "GIC": f"Geographic/institutional concentration {value:.4f}",
        "EIGEN": f"Eigenvector centrality {value:.4f} indicates unusual network position",
        "BETWEENNESS": f"Betweenness centrality {value:.4f} indicates brokerage role",
        "PAGERANK": f"PageRank {value:.4f} exceeds expected range",
        "COMMUNITY": f"Suspicious community membership (score: {value:.4f})",
        "CLIQUE": f"Citation clique detected (severity: {value:.4f})",
        "CV": f"Citation velocity {value:.4f} — abnormally fast accumulation",
        "SBD": f"Sleeping beauty pattern detected (score: {value:.4f})",
        "CTX": f"Contextual anomaly — {details.get('signal_count', '?')} independent signals",
    }
    return descriptions.get(indicator_type, f"Indicator {indicator_type} triggered at {value:.4f}")
