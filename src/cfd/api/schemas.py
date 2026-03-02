"""Pydantic v2 request/response schemas for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ErrorResponse(BaseModel):
    detail: str


class AuthorSummary(BaseModel):
    id: int | None = None
    surname: str | None = None
    full_name: str | None = None
    scopus_id: str | None = None
    orcid: str | None = None
    institution: str | None = None
    discipline: str | None = None
    h_index: int | None = None
    publication_count: int | None = None
    citation_count: int | None = None


class IndicatorDetail(BaseModel):
    type: str
    value: float
    details: dict = Field(default_factory=dict)


class AnalysisSummary(BaseModel):
    status: str = "completed"
    fraud_score: float = 0.0
    confidence_level: str = "normal"
    triggered_indicators: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TheoremDetail(BaseModel):
    theorem_number: int | None = None
    passed: bool = False
    details: dict = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    author: AuthorSummary
    fraud_score: float
    confidence_level: str
    triggered_indicators: list[str] = Field(default_factory=list)
    algorithm_version: str
    disclaimer: str = "This is a suspicion score, not a verdict. Final decision rests with a human."


class IndicatorsResponse(BaseModel):
    author: AuthorSummary
    indicators: list[IndicatorDetail] = Field(default_factory=list)
    algorithm_version: str
    disclaimer: str = "This is a suspicion score, not a verdict. Final decision rests with a human."


class ReportResponse(BaseModel):
    report_version: str = "1.0"
    algorithm_version: str = ""
    generated_at: str = ""
    disclaimer: str = "This is a suspicion score, not a verdict. Final decision rests with a human."
    author: AuthorSummary = Field(default_factory=AuthorSummary)
    analysis: AnalysisSummary = Field(default_factory=AnalysisSummary)
    indicators: list[IndicatorDetail] = Field(default_factory=list)
    theorem_results: list[TheoremDetail] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    label: str = ""
    type: str = "work"


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float = 1.0


class GraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class BatchResultItem(BaseModel):
    surname: str
    status: str = "completed"
    fraud_score: float | None = None
    confidence_level: str | None = None
    error: str | None = None


class BatchResponse(BaseModel):
    total: int = 0
    processed: int = 0
    results: list[BatchResultItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    disclaimer: str = "This is a suspicion score, not a verdict. Final decision rests with a human."


_ALLOWED_SENSITIVITY_KEYS = frozenset({
    "mcr_threshold", "scr_warn_threshold", "scr_high_threshold",
    "cb_threshold", "ta_z_threshold", "rla_threshold", "gic_threshold",
    "eigenvector_threshold", "betweenness_threshold", "pagerank_threshold",
    "community_density_ratio_threshold", "cantelli_z_threshold",
    "cv_threshold", "sbd_beauty_threshold", "sbd_suspicious_threshold",
    "ctx_independent_threshold", "ssd_similarity_threshold",
    "cc_per_paper_threshold", "ana_single_paper_coauthor_threshold",
    "pb_k_neighbors", "pb_min_peers", "cpc_divergence_threshold",
})


class SensitivityOverridesRequest(BaseModel):
    overrides: dict = Field(default_factory=dict)

    @field_validator("overrides")
    @classmethod
    def validate_keys(cls, v: dict) -> dict:
        bad = set(v) - _ALLOWED_SENSITIVITY_KEYS
        if bad:
            msg = f"Invalid sensitivity keys: {sorted(bad)}"
            raise ValueError(msg)
        return v


class WatchlistAddRequest(BaseModel):
    author_id: int
    reason: str | None = None
    notes: str | None = None


class WatchlistEntry(BaseModel):
    author_id: int | None = None
    reason: str | None = None
    notes: str | None = None
    is_active: bool = True
    created_at: str | None = None


class WatchlistHistoryEntry(BaseModel):
    snapshot_date: str | None = None
    fraud_score: float | None = None
    confidence_level: str | None = None
    indicator_values: dict | None = None
    algorithm_version: str | None = None


class AuditEntry(BaseModel):
    id: int | None = None
    timestamp: str | None = None
    action: str = ""
    target_author_id: int | None = None
    details: dict | None = None
    user_id: str | None = None


class VersionInfo(BaseModel):
    version: str = ""
    release_date: str | None = None
    indicator_count: int | None = None
    weights: dict | None = None
    thresholds: dict | None = None
    changelog: str | None = None
