"""Shared fixtures for integration tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cfd.analysis.pipeline import AnalysisPipeline
from cfd.config.settings import Settings
from cfd.data.openalex import OpenAlexStrategy

# --- Realistic OpenAlex mock responses ---

MOCK_AUTHOR_RESPONSE = {
    "id": "https://openalex.org/A100001",
    "display_name": "Oleksandr Ivanenko",
    "display_name_alternatives": ["O. Ivanenko"],
    "ids": {
        "orcid": "https://orcid.org/0000-0002-1234-5678",
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57200000001",
    },
    "affiliations": [{"institution": {"display_name": "Kyiv National University"}}],
    "topics": [{"display_name": "Computer Science"}],
    "x_concepts": [{"display_name": "AI"}],
    "summary_stats": {"h_index": 15},
    "works_count": 50,
    "cited_by_count": 500,
}


def _make_work(work_id: str, refs: list[str] | None = None, authors: list[dict] | None = None):
    """Build a single OpenAlex work response dict."""
    default_authors = [
        {
            "author": {"id": "https://openalex.org/A100001", "display_name": "O. Ivanenko"},
            "institutions": [{"display_name": "Kyiv U"}],
            "author_position": "first",
        }
    ]
    return {
        "id": f"https://openalex.org/{work_id}",
        "doi": f"https://doi.org/10.1234/{work_id.lower()}",
        "title": f"Publication {work_id}",
        "publication_date": "2023-06-15",
        "primary_location": {"source": {"display_name": "Test Journal"}},
        "cited_by_count": 5,
        "referenced_works": [f"https://openalex.org/{r}" for r in (refs or [])],
        "authorships": authors or default_authors,
        "abstract_inverted_index": {"Test": [0], "abstract": [1]},
    }


# 5 works with cross-references to build a non-trivial graph
MOCK_WORKS = [
    _make_work("W1001", refs=["W1002", "W1003"]),
    _make_work("W1002", refs=["W1001", "W1004"]),
    _make_work("W1003", refs=["W1005"]),
    _make_work("W1004", refs=["W1001", "W1003"]),
    _make_work("W1005", refs=["W1002"]),
]


def _build_mock_http(author_resp=None, works=None, citing_works=None):
    """Build a mock CachedHttpClient returning pre-programmed responses."""
    http = MagicMock()
    responses = []

    # fetch_author: search by orcid → returns results
    responses.append({"results": [author_resp or MOCK_AUTHOR_RESPONSE]})

    # fetch_publications: first page with works + no next cursor
    responses.append({
        "results": works or MOCK_WORKS,
        "meta": {"next_cursor": None},
    })

    # fetch_citations: citing works for each publication (one page each)
    citing = citing_works or []
    for cw in citing:
        responses.append({
            "results": cw,
            "meta": {"next_cursor": None},
        })

    http.get.side_effect = responses
    return http


@pytest.fixture
def integration_settings():
    """Settings with relaxed eligibility thresholds for testing."""
    return Settings(
        min_publications=1,
        min_citations=1,
        min_h_index=0,
        supabase_url="",
        supabase_key="",
    )


@pytest.fixture
def mock_http():
    """Mock HTTP client with realistic OpenAlex responses."""
    # Each publication gets one citing-works page (empty)
    citing = [[] for _ in MOCK_WORKS]
    return _build_mock_http(citing_works=citing)


@pytest.fixture
def integration_pipeline(mock_http, integration_settings):
    """Full pipeline with real OpenAlexStrategy + mock HTTP, no DB repos."""
    strategy = OpenAlexStrategy(mock_http)
    return AnalysisPipeline(
        strategy=strategy,
        settings=integration_settings,
    )
