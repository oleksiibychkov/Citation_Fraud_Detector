"""Tests for OpenAlexStrategy."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from cfd.data.models import AuthorProfile, Publication
from cfd.data.openalex import OpenAlexStrategy
from cfd.exceptions import AuthorNotFoundError

MOCK_AUTHOR = {
    "id": "https://openalex.org/A123456",
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

MOCK_WORK = {
    "id": "https://openalex.org/W12345",
    "doi": "https://doi.org/10.1234/test",
    "title": "Test Publication",
    "publication_date": "2023-06-15",
    "primary_location": {"source": {"display_name": "Test Journal"}},
    "cited_by_count": 10,
    "referenced_works": ["https://openalex.org/W11111"],
    "authorships": [
        {
            "author": {"id": "https://openalex.org/A123456", "display_name": "O. Ivanenko"},
            "institutions": [{"display_name": "Kyiv U"}],
            "author_position": "first",
        }
    ],
    "abstract_inverted_index": {"Hello": [0], "world": [1]},
}


def _make_strategy(responses):
    """Create strategy with mock HTTP client returning given responses in sequence."""
    http = MagicMock()
    http.get.side_effect = responses
    return OpenAlexStrategy(http)


class TestFetchAuthor:
    def test_fetch_by_orcid(self):
        strategy = _make_strategy([{"results": [MOCK_AUTHOR]}])
        profile = strategy.fetch_author("Ivanenko", orcid="0000-0002-1234-5678")
        assert profile.full_name == "Oleksandr Ivanenko"
        assert profile.orcid == "0000-0002-1234-5678"

    def test_fetch_by_scopus_id(self):
        strategy = _make_strategy([{"results": []}, {"results": [MOCK_AUTHOR]}])
        profile = strategy.fetch_author("Ivanenko", orcid="bad", scopus_id="57200000001")
        assert profile.scopus_id == "57200000001"

    def test_fetch_by_name(self):
        strategy = _make_strategy([{"results": [MOCK_AUTHOR]}])
        profile = strategy.fetch_author("Ivanenko")
        assert profile.surname == "Ivanenko"

    def test_fetch_not_found(self):
        strategy = _make_strategy([{"results": []}, {"results": []}])
        with pytest.raises(AuthorNotFoundError):
            strategy.fetch_author("Nobody", scopus_id="000")


class TestParseAuthor:
    def test_full_parse(self):
        strategy = _make_strategy([])
        profile = strategy._parse_author(MOCK_AUTHOR, "Ivanenko")
        assert profile.openalex_id == "A123456"
        assert profile.institution == "Kyiv National University"
        assert profile.h_index == 15
        assert profile.publication_count == 50
        assert profile.citation_count == 500

    def test_minimal_data(self):
        strategy = _make_strategy([])
        minimal = {"id": "", "ids": {}, "summary_stats": {}}
        profile = strategy._parse_author(minimal, "Test")
        assert profile.surname == "Test"
        assert profile.h_index is None


class TestExtractDiscipline:
    def test_from_topics(self):
        strategy = _make_strategy([])
        assert strategy._extract_discipline(MOCK_AUTHOR) == "Computer Science"

    def test_from_x_concepts(self):
        strategy = _make_strategy([])
        data = {"topics": [], "x_concepts": [{"display_name": "AI"}]}
        assert strategy._extract_discipline(data) == "AI"

    def test_none_when_empty(self):
        strategy = _make_strategy([])
        assert strategy._extract_discipline({}) is None


class TestFetchPublications:
    def test_pagination(self):
        strategy = _make_strategy([
            {"results": [MOCK_WORK], "meta": {"next_cursor": "abc"}},
            {"results": [MOCK_WORK], "meta": {"next_cursor": None}},
        ])
        author = AuthorProfile(openalex_id="A123456", surname="Ivanenko", source_api="openalex")
        pubs = strategy.fetch_publications(author)
        assert len(pubs) == 2

    def test_no_openalex_id(self):
        strategy = _make_strategy([])
        author = AuthorProfile(surname="Ivanenko", source_api="openalex")
        assert strategy.fetch_publications(author) == []


class TestParsePublication:
    def test_valid(self):
        strategy = _make_strategy([])
        pub = strategy._parse_publication(MOCK_WORK)
        assert pub is not None
        assert pub.work_id == "W12345"
        assert pub.journal == "Test Journal"
        assert pub.publication_date == date(2023, 6, 15)

    def test_no_work_id(self):
        strategy = _make_strategy([])
        assert strategy._parse_publication({"id": ""}) is None


class TestReconstructAbstract:
    def test_reconstruct(self):
        result = OpenAlexStrategy._reconstruct_abstract({"Hello": [0], "world": [1]})
        assert result == "Hello world"

    def test_none_input(self):
        assert OpenAlexStrategy._reconstruct_abstract(None) is None


class TestFetchCitations:
    def test_self_and_incoming(self):
        strategy = _make_strategy([
            {"results": [], "meta": {"next_cursor": None}},
        ])
        pub = Publication(
            work_id="W12345", title="Test", references_list=["W12345", "W99999"],
            source_api="openalex",
        )
        author = AuthorProfile(openalex_id="A123456", surname="Iv", source_api="openalex")
        citations = strategy.fetch_citations([pub], author)
        # 2 from references + 0 incoming
        assert len(citations) == 2
        # W12345 -> W12345 is self-citation
        self_cits = [c for c in citations if c.is_self_citation]
        assert len(self_cits) == 1
