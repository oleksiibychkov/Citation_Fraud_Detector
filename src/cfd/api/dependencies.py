"""FastAPI dependency injection for settings, DB, repos, and pipeline."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from cfd.config.settings import Settings

logger = logging.getLogger(__name__)


def get_settings(request: Request) -> Settings:
    """Get application settings from app state (set by create_app)."""
    return getattr(request.app.state, "settings", None) or Settings()


def get_supabase(request: Request) -> Any:
    """Get Supabase client from app state. Raises 503 if unavailable."""
    client = getattr(request.app.state, "supabase", None)
    if client is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        )
    return client


def get_repos(client=Depends(get_supabase)) -> dict[str, Any]:
    """Build all repository instances from Supabase client."""
    from cfd.db.repositories.algorithm_versions import AlgorithmVersionRepository
    from cfd.db.repositories.audit import AuditLogRepository
    from cfd.db.repositories.authors import AuthorRepository
    from cfd.db.repositories.citations import CitationRepository
    from cfd.db.repositories.fraud_scores import FraudScoreRepository
    from cfd.db.repositories.indicators import IndicatorRepository
    from cfd.db.repositories.publications import PublicationRepository
    from cfd.db.repositories.snapshots import SnapshotRepository
    from cfd.db.repositories.watchlist import WatchlistRepository

    return {
        "author": AuthorRepository(client),
        "fraud_score": FraudScoreRepository(client),
        "indicator": IndicatorRepository(client),
        "citation": CitationRepository(client),
        "publication": PublicationRepository(client),
        "watchlist": WatchlistRepository(client),
        "audit": AuditLogRepository(client),
        "algorithm": AlgorithmVersionRepository(client),
        "snapshot": SnapshotRepository(client),
    }


def get_pipeline(
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """Build analysis pipeline (for batch analyze endpoint)."""
    from cfd.analysis.pipeline import AnalysisPipeline
    from cfd.data.http_client import CachedHttpClient, RateLimiter
    from cfd.data.openalex import OpenAlexStrategy

    supabase = getattr(request.app.state, "supabase", None)

    rate_limiter = RateLimiter(settings.openalex_requests_per_second)
    http_client = CachedHttpClient(supabase, rate_limiter, settings.cache_ttl_days)
    strategy = OpenAlexStrategy(http_client)

    # Build repos if DB available
    author_repo = pub_repo = cit_repo = ind_repo = score_repo = None
    if supabase is not None:
        try:
            from cfd.db.repositories.authors import AuthorRepository
            from cfd.db.repositories.citations import CitationRepository
            from cfd.db.repositories.fraud_scores import FraudScoreRepository
            from cfd.db.repositories.indicators import IndicatorRepository
            from cfd.db.repositories.publications import PublicationRepository

            author_repo = AuthorRepository(supabase)
            pub_repo = PublicationRepository(supabase)
            cit_repo = CitationRepository(supabase)
            ind_repo = IndicatorRepository(supabase)
            score_repo = FraudScoreRepository(supabase)
        except Exception:
            logger.warning("Failed to init DB repos for pipeline", exc_info=True)

    return AnalysisPipeline(
        strategy=strategy,
        settings=settings,
        author_repo=author_repo,
        pub_repo=pub_repo,
        cit_repo=cit_repo,
        ind_repo=ind_repo,
        score_repo=score_repo,
    )
