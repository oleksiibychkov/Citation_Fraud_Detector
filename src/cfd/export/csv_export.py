"""CSV report generation."""

from __future__ import annotations

import csv
from pathlib import Path

from cfd.analysis.pipeline import AnalysisResult
from cfd.config.settings import Settings


def export_to_csv(result: AnalysisResult, output_path: Path, settings: Settings | None = None) -> None:
    """Export single author analysis result to CSV."""
    s = settings or Settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header info
        writer.writerow(["# Author", result.author_profile.full_name or result.author_profile.surname])
        writer.writerow(["# Scopus ID", result.author_profile.scopus_id or ""])
        writer.writerow(["# ORCID", result.author_profile.orcid or ""])
        writer.writerow(["# Fraud Score", result.fraud_score])
        writer.writerow(["# Confidence Level", result.confidence_level])
        writer.writerow(["# Algorithm Version", s.algorithm_version])
        writer.writerow([])

        # Indicators table
        writer.writerow(["indicator_type", "value", "triggered", "details"])
        for ind in result.indicators:
            triggered = ind.indicator_type in result.triggered_indicators
            details_str = "; ".join(f"{k}={v}" for k, v in ind.details.items() if k != "status")
            writer.writerow([
                ind.indicator_type,
                round(ind.value, 6),
                "YES" if triggered else "NO",
                details_str[:200],
            ])


def export_ranking_csv(results: list[AnalysisResult], output_path: Path, settings: Settings | None = None) -> None:
    """Export anti-ranking: authors sorted by Fraud Score (highest first)."""
    s = settings or Settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_results = sorted(results, key=lambda r: r.fraud_score, reverse=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rank", "surname", "full_name", "scopus_id", "orcid",
            "fraud_score", "confidence_level", "triggered_count", "algorithm_version",
        ])
        for i, r in enumerate(sorted_results, 1):
            writer.writerow([
                i,
                r.author_profile.surname,
                r.author_profile.full_name or "",
                r.author_profile.scopus_id or "",
                r.author_profile.orcid or "",
                round(r.fraud_score, 4),
                r.confidence_level,
                len(r.triggered_indicators),
                s.algorithm_version,
            ])
