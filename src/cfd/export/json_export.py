"""JSON report generation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from cfd.analysis.pipeline import AnalysisResult
from cfd.config.settings import Settings


def export_to_json(result: AnalysisResult, output_path: Path, settings: Settings | None = None) -> None:
    """Export analysis result as a structured JSON report."""
    s = settings or Settings()

    report = {
        "report_version": "1.0",
        "algorithm_version": s.algorithm_version,
        "generated_at": datetime.now(UTC).isoformat(),
        "disclaimer": "This is a suspicion score, not a verdict. Final decision rests with a human.",
        "author": {
            "surname": result.author_profile.surname,
            "full_name": result.author_profile.full_name,
            "scopus_id": result.author_profile.scopus_id,
            "orcid": result.author_profile.orcid,
            "institution": result.author_profile.institution,
            "discipline": result.author_profile.discipline,
            "h_index": result.author_profile.h_index,
            "publication_count": result.author_profile.publication_count,
            "citation_count": result.author_profile.citation_count,
        },
        "analysis": {
            "status": result.status,
            "fraud_score": result.fraud_score,
            "confidence_level": result.confidence_level,
            "triggered_indicators": result.triggered_indicators,
            "warnings": result.warnings,
        },
        "indicators": [
            {
                "type": ind.indicator_type,
                "value": round(ind.value, 6),
                "details": ind.details,
            }
            for ind in result.indicators
        ],
        "theorem_results": [
            {
                "theorem_number": tr.theorem_number,
                "passed": tr.passed,
                "details": tr.details,
            }
            for tr in result.theorem_results
        ],
        "thresholds": {
            "min_publications": s.min_publications,
            "min_citations": s.min_citations,
            "min_h_index": s.min_h_index,
            "mcr_threshold": s.mcr_threshold,
            "scr_warn_threshold": s.scr_warn_threshold,
            "scr_high_threshold": s.scr_high_threshold,
            "cb_threshold": s.cb_threshold,
            "ta_z_threshold": s.ta_z_threshold,
            "rla_threshold": s.rla_threshold,
            "gic_threshold": s.gic_threshold,
            "eigenvector_threshold": s.eigenvector_threshold,
            "betweenness_threshold": s.betweenness_threshold,
            "pagerank_threshold": s.pagerank_threshold,
            "community_density_ratio_threshold": s.community_density_ratio_threshold,
            "cantelli_z_threshold": s.cantelli_z_threshold,
            "cv_threshold": s.cv_threshold,
            "sbd_beauty_threshold": s.sbd_beauty_threshold,
            "sbd_suspicious_threshold": s.sbd_suspicious_threshold,
            "ctx_independent_threshold": s.ctx_independent_threshold,
            "ssd_similarity_threshold": s.ssd_similarity_threshold,
            "ssd_interval_days": s.ssd_interval_days,
            "cc_per_paper_threshold": s.cc_per_paper_threshold,
            "ana_single_paper_coauthor_threshold": s.ana_single_paper_coauthor_threshold,
            "pb_k_neighbors": s.pb_k_neighbors,
            "pb_min_peers": s.pb_min_peers,
            "cpc_divergence_threshold": s.cpc_divergence_threshold,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)


def result_to_dict(result: AnalysisResult, settings: Settings | None = None) -> dict:
    """Convert analysis result to a dictionary (for programmatic use)."""
    s = settings or Settings()
    return {
        "author": {
            "surname": result.author_profile.surname,
            "full_name": result.author_profile.full_name,
        },
        "status": result.status,
        "fraud_score": result.fraud_score,
        "confidence_level": result.confidence_level,
        "triggered_indicators": result.triggered_indicators,
        "warnings": result.warnings,
        "indicators": {ind.indicator_type: round(ind.value, 6) for ind in result.indicators},
        "theorem_results": [
            {"theorem_number": tr.theorem_number, "passed": tr.passed}
            for tr in result.theorem_results
        ],
        "algorithm_version": s.algorithm_version,
    }
