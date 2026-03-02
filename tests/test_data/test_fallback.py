"""Tests for FallbackStrategy."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cfd.data.fallback import FallbackStrategy
from cfd.data.models import AuthorProfile, Citation, Publication
from cfd.exceptions import APIError, AuthorNotFoundError

MOCK_PROFILE = AuthorProfile(
    surname="Ivanenko",
    full_name="Oleksandr Ivanenko",
    source_api="openalex",
)

MOCK_PUBS = [
    Publication(work_id="W1", title="Test", source_api="openalex"),
]

MOCK_CITATIONS = [
    Citation(source_work_id="W2", target_work_id="W1", source_api="openalex"),
]


class TestFetchAuthor:
    def test_primary_success(self):
        primary = MagicMock()
        secondary = MagicMock()
        primary.fetch_author.return_value = MOCK_PROFILE

        strategy = FallbackStrategy(primary, secondary)
        result = strategy.fetch_author("Ivanenko", orcid="0000-0002-1234-5678")
        assert result.surname == "Ivanenko"
        secondary.fetch_author.assert_not_called()

    def test_api_error_fallback(self):
        primary = MagicMock()
        secondary = MagicMock()
        primary.fetch_author.side_effect = APIError("timeout")
        secondary.fetch_author.return_value = MOCK_PROFILE

        strategy = FallbackStrategy(primary, secondary)
        result = strategy.fetch_author("Ivanenko")
        assert result.surname == "Ivanenko"
        secondary.fetch_author.assert_called_once()

    def test_not_found_fallback(self):
        primary = MagicMock()
        secondary = MagicMock()
        primary.fetch_author.side_effect = AuthorNotFoundError("not found")
        secondary.fetch_author.return_value = MOCK_PROFILE

        strategy = FallbackStrategy(primary, secondary)
        result = strategy.fetch_author("Ivanenko")
        assert result.surname == "Ivanenko"

    def test_both_fail(self):
        primary = MagicMock()
        secondary = MagicMock()
        primary.fetch_author.side_effect = APIError("primary fail")
        secondary.fetch_author.side_effect = AuthorNotFoundError("secondary fail")

        strategy = FallbackStrategy(primary, secondary)
        with pytest.raises(AuthorNotFoundError):
            strategy.fetch_author("Nobody")


class TestFetchPublications:
    def test_fallback(self):
        primary = MagicMock()
        secondary = MagicMock()
        primary.fetch_publications.side_effect = APIError("timeout")
        secondary.fetch_publications.return_value = MOCK_PUBS

        strategy = FallbackStrategy(primary, secondary)
        result = strategy.fetch_publications(MOCK_PROFILE)
        assert len(result) == 1
        secondary.fetch_publications.assert_called_once()


class TestFetchCitations:
    def test_fallback(self):
        primary = MagicMock()
        secondary = MagicMock()
        primary.fetch_citations.side_effect = APIError("timeout")
        secondary.fetch_citations.return_value = MOCK_CITATIONS

        strategy = FallbackStrategy(primary, secondary)
        result = strategy.fetch_citations(MOCK_PUBS, MOCK_PROFILE)
        assert len(result) == 1
        secondary.fetch_citations.assert_called_once()
