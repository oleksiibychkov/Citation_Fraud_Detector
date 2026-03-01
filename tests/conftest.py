"""Shared test fixtures and mocks."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from cfd.config.settings import Settings
from cfd.data.models import AuthorData, AuthorProfile, Citation, Publication


@pytest.fixture
def settings():
    """Test settings with defaults."""
    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        scopus_api_key="test-scopus-key",
    )


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = MagicMock()

    # Mock table operations chain
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.lt.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock

    execute_result = MagicMock()
    execute_result.data = []
    execute_result.count = 0
    table_mock.execute.return_value = execute_result

    client.table.return_value = table_mock
    return client


@pytest.fixture
def sample_author_profile():
    """Sample author profile for testing."""
    return AuthorProfile(
        scopus_id="57200000001",
        orcid="0000-0002-1234-5678",
        openalex_id="A123456789",
        surname="Ivanenko",
        full_name="Oleksandr Ivanenko",
        display_name_variants=["Oleksandr Ivanenko", "O. Ivanenko"],
        institution="Kyiv National University",
        discipline="Computer Science",
        h_index=15,
        publication_count=50,
        citation_count=500,
        source_api="openalex",
    )


@pytest.fixture
def sample_publications():
    """Sample publications for testing."""
    return [
        Publication(
            work_id=f"W{i}",
            doi=f"10.1234/test.{i}",
            title=f"Test Publication {i}",
            publication_date=date(2020 + (i % 5), 1 + (i % 12), 1),
            journal="Test Journal",
            citation_count=10 * i,
            references_list=[f"W{j}" for j in range(max(0, i - 3), i)],
            source_api="openalex",
        )
        for i in range(1, 11)
    ]


@pytest.fixture
def sample_citations():
    """Sample citations for testing."""
    citations = []
    # Self-citations
    for i in range(1, 6):
        citations.append(
            Citation(
                source_work_id=f"W{i}",
                target_work_id=f"W{i - 1}" if i > 1 else "W10",
                source_author_id=1,
                target_author_id=1,
                citation_date=date(2022, i, 1),
                is_self_citation=True,
                source_api="openalex",
            )
        )
    # External citations
    for i in range(6, 16):
        citations.append(
            Citation(
                source_work_id=f"EXT{i}",
                target_work_id=f"W{i % 10 + 1}",
                source_author_id=i,
                target_author_id=1,
                citation_date=date(2023, i % 12 + 1, 1),
                is_self_citation=False,
                source_api="openalex",
            )
        )
    return citations


@pytest.fixture
def sample_author_data(sample_author_profile, sample_publications, sample_citations):
    """Complete sample author data for testing."""
    return AuthorData(
        profile=sample_author_profile,
        publications=sample_publications,
        citations=sample_citations,
    )
