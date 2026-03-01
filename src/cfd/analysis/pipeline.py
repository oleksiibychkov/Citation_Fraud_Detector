"""Main analysis pipeline orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from cfd.analysis.eligibility import check_eligibility
from cfd.config.settings import Settings
from cfd.data.models import AuthorProfile
from cfd.data.strategy import DataSourceStrategy
from cfd.db.repositories.authors import AuthorRepository
from cfd.db.repositories.citations import CitationRepository
from cfd.db.repositories.fraud_scores import FraudScoreRepository
from cfd.db.repositories.indicators import IndicatorRepository
from cfd.db.repositories.publications import PublicationRepository
from cfd.graph.builder import build_citation_graph
from cfd.graph.metrics import (
    IndicatorResult,
    compute_cb,
    compute_hta,
    compute_mcr_from_author_data,
    compute_scr,
    compute_ta,
)
from cfd.graph.scoring import DEFAULT_WEIGHTS, compute_fraud_score

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Complete result of an author analysis."""

    author_profile: AuthorProfile
    indicators: list[IndicatorResult] = field(default_factory=list)
    fraud_score: float = 0.0
    confidence_level: str = "normal"
    triggered_indicators: list[str] = field(default_factory=list)
    status: str = "completed"
    warnings: list[str] = field(default_factory=list)


class AnalysisPipeline:
    """Orchestrates the full analysis flow: collect -> check -> graph -> score -> persist."""

    def __init__(
        self,
        strategy: DataSourceStrategy,
        settings: Settings,
        author_repo: AuthorRepository | None = None,
        pub_repo: PublicationRepository | None = None,
        cit_repo: CitationRepository | None = None,
        ind_repo: IndicatorRepository | None = None,
        score_repo: FraudScoreRepository | None = None,
    ):
        self._strategy = strategy
        self._settings = settings
        self._author_repo = author_repo
        self._pub_repo = pub_repo
        self._cit_repo = cit_repo
        self._ind_repo = ind_repo
        self._score_repo = score_repo

    def analyze(
        self,
        surname: str,
        *,
        scopus_id: str | None = None,
        orcid: str | None = None,
    ) -> AnalysisResult:
        """Run full analysis pipeline for a single author."""
        warnings: list[str] = []

        # Step 1: Collect data from API
        logger.info("Collecting data for %s...", surname)
        author_data = self._strategy.collect(surname, scopus_id=scopus_id, orcid=orcid)

        # Step 2: Check eligibility
        eligible, reason = check_eligibility(author_data.profile, self._settings)
        if not eligible:
            logger.info("Author %s: %s", surname, reason)
            return AnalysisResult(
                author_profile=author_data.profile,
                status="insufficient_data",
                warnings=[reason],
            )

        # Step 3: Persist data to DB (if repos available)
        author_id = self._persist_data(author_data)

        # Step 4: Build graph
        logger.info("Building citation graph...")
        build_citation_graph(author_data)  # validates graph structure

        # Step 5: Compute indicators
        logger.info("Computing indicators...")
        indicators: list[IndicatorResult] = []
        indicators.append(compute_scr(author_data))
        indicators.append(compute_mcr_from_author_data(author_data))
        indicators.append(compute_cb(author_data))
        indicators.append(compute_ta(author_data))
        indicators.append(compute_hta(author_data))

        # Step 6: Compute fraud score
        score, confidence, triggered = compute_fraud_score(indicators, self._settings)

        # Step 7: Persist results
        if author_id:
            self._persist_results(author_id, indicators, score, confidence, triggered)

        logger.info("Analysis complete for %s: score=%.4f, level=%s", surname, score, confidence)

        return AnalysisResult(
            author_profile=author_data.profile,
            indicators=indicators,
            fraud_score=score,
            confidence_level=confidence,
            triggered_indicators=triggered,
            status="completed",
            warnings=warnings,
        )

    def _persist_data(self, author_data) -> int | None:
        """Persist collected author data to database. Returns author_id."""
        if not self._author_repo:
            return None

        try:
            stored = self._author_repo.upsert(author_data.profile)
            author_id = stored.get("id")

            if author_id and self._pub_repo:
                self._pub_repo.upsert_many(author_id, author_data.publications)

            if author_id and self._cit_repo:
                self._cit_repo.upsert_many(author_data.citations, target_author_id=author_id)

            return author_id
        except Exception:
            logger.warning("Failed to persist data to DB", exc_info=True)
            return None

    def _persist_results(
        self,
        author_id: int,
        indicators: list[IndicatorResult],
        score: float,
        confidence: str,
        triggered: list[str],
    ) -> None:
        """Persist computed indicators and fraud score to database."""
        try:
            if self._ind_repo:
                ind_dicts = [
                    {
                        "indicator_type": ind.indicator_type,
                        "value": ind.value,
                        "details": ind.details,
                    }
                    for ind in indicators
                ]
                self._ind_repo.save_many(author_id, ind_dicts, self._settings.algorithm_version)

            if self._score_repo:
                indicator_weights = {k: v for k, v in DEFAULT_WEIGHTS.items()}
                indicator_values = {ind.indicator_type: ind.value for ind in indicators}
                self._score_repo.save(
                    author_id=author_id,
                    score=score,
                    confidence_level=confidence,
                    indicator_weights=indicator_weights,
                    indicator_values=indicator_values,
                    triggered_indicators=triggered,
                    algorithm_version=self._settings.algorithm_version,
                )
        except Exception:
            logger.warning("Failed to persist results to DB", exc_info=True)
