"""Author analysis endpoints — read cached results from DB."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from cfd.api.auth import APIKeyInfo, require_role
from cfd.api.dependencies import get_repos, get_settings
from cfd.api.schemas import (
    AnalysisSummary,
    AuthorSummary,
    GraphEdge,
    GraphNode,
    GraphResponse,
    IndicatorDetail,
    IndicatorsResponse,
    ReportResponse,
    ScoreResponse,
)
from cfd.config.settings import Settings
from cfd.exceptions import AuthorNotFoundError

router = APIRouter(prefix="/author", tags=["Author"])


def _author_summary(author: dict) -> AuthorSummary:
    return AuthorSummary(
        id=author.get("id"),
        surname=author.get("surname"),
        full_name=author.get("full_name"),
        scopus_id=author.get("scopus_id"),
        orcid=author.get("orcid"),
        institution=author.get("institution"),
        discipline=author.get("discipline"),
        h_index=author.get("h_index"),
        publication_count=author.get("publication_count"),
        citation_count=author.get("citation_count"),
    )


def _get_author_or_404(repos: dict[str, Any], author_id: int) -> dict:
    author = repos["author"].get_by_id(author_id)
    if not author:
        raise AuthorNotFoundError(f"Author {author_id} not found")
    return author


@router.get("/{author_id}/report", response_model=ReportResponse)
def get_author_report(
    author_id: int,
    key_info: APIKeyInfo = Depends(require_role("reader", "analyst", "admin")),
    repos: dict = Depends(get_repos),
    settings: Settings = Depends(get_settings),
):
    """Full analysis report for an author."""
    author = _get_author_or_404(repos, author_id)
    score_data = repos["fraud_score"].get_latest_by_author(author_id)
    indicators = repos["indicator"].get_by_author_id(author_id)

    repos["audit"].log(
        "view_report", target_author_id=author_id,
        details={"api_key": key_info.name}, user_id=key_info.name,
        api_key_id=key_info.key_id,
    )

    return ReportResponse(
        algorithm_version=settings.algorithm_version,
        generated_at=datetime.now(UTC).isoformat(),
        author=_author_summary(author),
        analysis=AnalysisSummary(
            fraud_score=score_data.get("score", 0.0) if score_data else 0.0,
            confidence_level=score_data.get("confidence_level", "normal") if score_data else "normal",
            triggered_indicators=score_data.get("triggered_indicators", []) if score_data else [],
        ),
        indicators=[
            IndicatorDetail(
                type=ind.get("indicator_type", ""),
                value=ind.get("value", 0.0),
                details=ind.get("details", {}),
            )
            for ind in indicators
        ],
    )


@router.get("/{author_id}/score", response_model=ScoreResponse)
def get_author_score(
    author_id: int,
    key_info: APIKeyInfo = Depends(require_role("reader", "analyst", "admin")),
    repos: dict = Depends(get_repos),
    settings: Settings = Depends(get_settings),
):
    """Get current fraud score for an author."""
    author = _get_author_or_404(repos, author_id)
    score_data = repos["fraud_score"].get_latest_by_author(author_id)

    return ScoreResponse(
        author=_author_summary(author),
        fraud_score=score_data.get("score", 0.0) if score_data else 0.0,
        confidence_level=score_data.get("confidence_level", "normal") if score_data else "normal",
        triggered_indicators=score_data.get("triggered_indicators", []) if score_data else [],
        algorithm_version=settings.algorithm_version,
    )


@router.get("/{author_id}/indicators", response_model=IndicatorsResponse)
def get_author_indicators(
    author_id: int,
    key_info: APIKeyInfo = Depends(require_role("reader", "analyst", "admin")),
    repos: dict = Depends(get_repos),
    settings: Settings = Depends(get_settings),
):
    """Get detailed indicator breakdown for an author."""
    author = _get_author_or_404(repos, author_id)
    indicators = repos["indicator"].get_by_author_id(author_id)

    return IndicatorsResponse(
        author=_author_summary(author),
        indicators=[
            IndicatorDetail(
                type=ind.get("indicator_type", ""),
                value=ind.get("value", 0.0),
                details=ind.get("details", {}),
            )
            for ind in indicators
        ],
        algorithm_version=settings.algorithm_version,
    )


@router.get("/{author_id}/graph", response_model=GraphResponse)
def get_author_graph(
    author_id: int,
    key_info: APIKeyInfo = Depends(require_role("reader", "analyst", "admin")),
    repos: dict = Depends(get_repos),
):
    """Get citation graph data as nodes + edges JSON."""
    _get_author_or_404(repos, author_id)

    citations = repos["citation"].get_by_target_author(author_id)
    nodes_set: set[str] = set()
    edges: list[GraphEdge] = []

    for cit in citations:
        src = cit.get("source_work_id", "")
        tgt = cit.get("target_work_id", "")
        if src and tgt:
            nodes_set.add(src)
            nodes_set.add(tgt)
            edges.append(GraphEdge(source=src, target=tgt))

    nodes = [GraphNode(id=nid, label=nid) for nid in sorted(nodes_set)]
    return GraphResponse(nodes=nodes, edges=edges)
