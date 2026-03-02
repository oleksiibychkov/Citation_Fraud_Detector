"""Tests for ScopusStrategy."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from cfd.data.models import AuthorProfile, Publication
from cfd.data.scopus import ScopusStrategy
from cfd.exceptions import AuthorNotFoundError, ValidationError

MOCK_SCOPUS_AUTHOR = {
    "coredata": {
        "dc:identifier": "AUTHOR_ID:57200000001",
        "h-index": "15",
        "document-count": "50",
        "citation-count": "500",
        "link": [],
    },
    "author-profile": {
        "preferred-name": {"given-name": "Oleksandr", "surname": "Ivanenko"},
        "affiliation-history": {
            "affiliation": [{"ip-doc": {"afdispname": "Kyiv National University"}}]
        },
    },
    "subject-areas": {"subject-area": [{"$": "Computer Science"}]},
}

MOCK_SCOPUS_ENTRY = {
    "eid": "2-s2.0-85123456789",
    "prism:doi": "10.1234/test",
    "dc:title": "Test Publication",
    "prism:coverDate": "2023-06-15",
    "prism:publicationName": "Test Journal",
    "citedby-count": "10",
}


def _make_strategy(responses):
    http = MagicMock()
    http.get.side_effect = responses
    return ScopusStrategy(http, api_key="test-key")


class TestScopusInit:
    def test_requires_api_key(self):
        with pytest.raises(ValidationError):
            ScopusStrategy(MagicMock(), api_key="")


class TestFetchAuthor:
    def test_by_scopus_id(self):
        strategy = _make_strategy([
            {"author-retrieval-response": [MOCK_SCOPUS_AUTHOR]},
        ])
        profile = strategy.fetch_author("Ivanenko", scopus_id="57200000001")
        assert profile.full_name == "Oleksandr Ivanenko"

    def test_by_orcid(self):
        strategy = _make_strategy([
            {"search-results": {"entry": [{"dc:identifier": "AUTHOR_ID:57200000001"}]}},
            {"author-retrieval-response": [MOCK_SCOPUS_AUTHOR]},
        ])
        profile = strategy.fetch_author("Ivanenko", orcid="0000-0002-1234-5678")
        assert profile.scopus_id == "57200000001"

    def test_by_name(self):
        strategy = _make_strategy([
            {"search-results": {"entry": [{"dc:identifier": "AUTHOR_ID:57200000001"}]}},
            {"author-retrieval-response": [MOCK_SCOPUS_AUTHOR]},
        ])
        profile = strategy.fetch_author("Ivanenko")
        assert profile.surname == "Ivanenko"

    def test_not_found(self):
        # Test the clean not-found path via API error
        http = MagicMock()
        http.get.side_effect = Exception("API error")
        s = ScopusStrategy(http, api_key="k")
        with pytest.raises(AuthorNotFoundError):
            s.fetch_author("Nobody", scopus_id="000")


class TestParseAuthor:
    def test_full_parse(self):
        strategy = _make_strategy([])
        profile = strategy._parse_author(MOCK_SCOPUS_AUTHOR, "Ivanenko")
        assert profile.scopus_id == "57200000001"
        assert profile.institution == "Kyiv National University"
        assert profile.discipline == "Computer Science"
        assert profile.h_index == 15
        assert profile.publication_count == 50


class TestFetchPublications:
    def test_pagination(self):
        strategy = _make_strategy([
            {
                "search-results": {
                    "entry": [MOCK_SCOPUS_ENTRY],
                    "opensearch:totalResults": "30",
                },
            },
            {
                "search-results": {
                    "entry": [MOCK_SCOPUS_ENTRY],
                    "opensearch:totalResults": "30",
                },
            },
        ])
        author = AuthorProfile(scopus_id="57200000001", surname="Iv", source_api="scopus")
        pubs = strategy.fetch_publications(author)
        assert len(pubs) == 2

    def test_no_scopus_id(self):
        strategy = _make_strategy([])
        author = AuthorProfile(surname="Iv", source_api="scopus")
        assert strategy.fetch_publications(author) == []


class TestParsePublication:
    def test_valid(self):
        strategy = _make_strategy([])
        pub = strategy._parse_publication(MOCK_SCOPUS_ENTRY)
        assert pub is not None
        assert pub.work_id == "2-s2.0-85123456789"
        assert pub.journal == "Test Journal"
        assert pub.publication_date == date(2023, 6, 15)

    def test_no_eid(self):
        strategy = _make_strategy([])
        assert strategy._parse_publication({"eid": ""}) is None


class TestFetchCitations:
    def test_from_references(self):
        strategy = _make_strategy([])
        pub = Publication(
            work_id="E1", title="Test", references_list=["REF1", "REF2"],
            source_api="scopus",
        )
        author = AuthorProfile(scopus_id="57200000001", surname="Iv", source_api="scopus")
        citations = strategy.fetch_citations([pub], author)
        assert len(citations) == 2
