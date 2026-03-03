"""Discipline baselines for indicator normalization."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DisciplineBaseline:
    """Statistical baseline for a scientific discipline."""

    discipline: str
    avg_scr: float
    std_scr: float
    avg_citations_per_paper: float = 8.0
    avg_h_index_growth_rate: float = 1.0
    citation_half_life_years: float = 6.0
    avg_papers_per_year: float = 3.0
    journal_quartile_medians: dict = field(default_factory=lambda: {"Q1": 15.0, "Q2": 8.0, "Q3": 4.0, "Q4": 2.0})


# Hardcoded defaults from published scientometric literature
DEFAULT_BASELINES: dict[str, DisciplineBaseline] = {
    "Computer Science": DisciplineBaseline(
        discipline="Computer Science",
        avg_scr=0.12, std_scr=0.08,
        avg_citations_per_paper=8.5, avg_h_index_growth_rate=1.2,
        citation_half_life_years=5.5, avg_papers_per_year=3.0,
        journal_quartile_medians={"Q1": 15.0, "Q2": 8.0, "Q3": 4.0, "Q4": 2.0},
    ),
    "Medicine": DisciplineBaseline(
        discipline="Medicine",
        avg_scr=0.08, std_scr=0.06,
        avg_citations_per_paper=12.0, avg_h_index_growth_rate=1.5,
        citation_half_life_years=7.0, avg_papers_per_year=4.5,
        journal_quartile_medians={"Q1": 25.0, "Q2": 12.0, "Q3": 6.0, "Q4": 3.0},
    ),
    "Physics": DisciplineBaseline(
        discipline="Physics",
        avg_scr=0.10, std_scr=0.07,
        avg_citations_per_paper=10.0, avg_h_index_growth_rate=1.3,
        citation_half_life_years=6.0, avg_papers_per_year=3.5,
        journal_quartile_medians={"Q1": 20.0, "Q2": 10.0, "Q3": 5.0, "Q4": 2.5},
    ),
    "Chemistry": DisciplineBaseline(
        discipline="Chemistry",
        avg_scr=0.09, std_scr=0.06,
        avg_citations_per_paper=11.0, avg_h_index_growth_rate=1.4,
        citation_half_life_years=6.5, avg_papers_per_year=4.0,
        journal_quartile_medians={"Q1": 22.0, "Q2": 11.0, "Q3": 5.5, "Q4": 2.5},
    ),
    "Social Sciences": DisciplineBaseline(
        discipline="Social Sciences",
        avg_scr=0.15, std_scr=0.10,
        avg_citations_per_paper=6.0, avg_h_index_growth_rate=0.8,
        citation_half_life_years=8.0, avg_papers_per_year=2.0,
        journal_quartile_medians={"Q1": 10.0, "Q2": 5.0, "Q3": 3.0, "Q4": 1.5},
    ),
}

# Cross-discipline average (used as fallback)
_CROSS_DISCIPLINE = DisciplineBaseline(
    discipline="Cross-discipline",
    avg_scr=0.11, std_scr=0.08,
    avg_citations_per_paper=9.0, avg_h_index_growth_rate=1.2,
    citation_half_life_years=6.5, avg_papers_per_year=3.5,
    journal_quartile_medians={"Q1": 18.0, "Q2": 9.0, "Q3": 4.5, "Q4": 2.0},
)


def get_baseline(discipline: str | None, repo=None) -> DisciplineBaseline:
    """Get baseline for a discipline. Falls back to cross-discipline average.

    Tries DB repo first (if provided), then static defaults.
    """
    if discipline and repo:
        try:
            row = repo.get_by_discipline(discipline)
            if row:
                return DisciplineBaseline(
                    discipline=row["discipline"],
                    avg_scr=row["avg_scr"],
                    std_scr=row["std_scr"],
                    avg_citations_per_paper=row.get("avg_citations_per_paper", 8.0),
                    avg_h_index_growth_rate=row.get("avg_h_index_growth_rate", 1.0),
                    citation_half_life_years=row.get("citation_half_life_years", 6.0),
                    avg_papers_per_year=row.get("avg_papers_per_year", 3.0),
                    journal_quartile_medians=row.get("journal_quartile_medians", {}),
                )
        except Exception:
            logger.warning("Failed to fetch baseline from DB", exc_info=True)

    if discipline:
        # Try exact match
        if discipline in DEFAULT_BASELINES:
            return DEFAULT_BASELINES[discipline]
        # Try case-insensitive partial match
        dl = discipline.lower()
        for name, baseline in DEFAULT_BASELINES.items():
            if dl in name.lower() or name.lower() in dl:
                return baseline

    return _CROSS_DISCIPLINE


def normalize_by_discipline(value: float, mean: float, std: float) -> float:
    """Z-score normalization relative to discipline baseline.

    Returns how many standard deviations value is above the mean.
    Positive = above average (more suspicious for SCR-like metrics).
    """
    if std <= 0:
        return 0.0
    return (value - mean) / std


def get_journal_quartile(journal_name: str | None, baseline: DisciplineBaseline) -> str:
    """Determine journal quartile. Returns Q1/Q2/Q3/Q4, defaults to Q2 if unknown.

    Uses expanded keyword heuristics covering major publishers and tiers.
    In a production system this should be replaced by a journal classification database
    (e.g., Scimago JR data, Scopus Source List, or OpenAlex source classification).
    """
    if not journal_name:
        return "Q2"
    jl = journal_name.lower()

    # Q1: top-tier journals and well-known high-impact series
    q1_keywords = (
        "nature", "science", "lancet", "cell", "nejm",
        "new england journal", "jama", "bmj", "annals of",
        "ieee transactions", "ieee journal", "acm computing surveys",
        "proceedings of the national academy", "pnas",
        "physical review letters", "angewandte chemie",
        "journal of the american chemical", "advanced materials",
        "chemical reviews", "reviews of modern physics",
        "annual review", "nature review",
    )
    if any(w in jl for w in q1_keywords):
        return "Q1"

    # Q2: solid mid-tier journals
    q2_keywords = (
        "plos one", "plos ", "bmc ", "frontiers in", "scientific reports",
        "ieee access", "sensors", "applied sciences", "materials",
        "journal of", "international journal",
        "computers", "information sciences", "neurocomputing",
    )
    if any(w in jl for w in q2_keywords):
        return "Q2"

    # Q4: known predatory/low-impact indicators
    q4_keywords = (
        "preprint", "arxiv", "ssrn", "working paper",
        "advances in", "recent patents",
    )
    if any(w in jl for w in q4_keywords):
        return "Q4"

    # Q3: everything else that has a recognizable journal name
    if len(jl) > 5:
        return "Q3"

    return "Q2"  # very short names default to Q2
