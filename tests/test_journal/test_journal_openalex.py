"""Tests for journal OpenAlex data collection."""

from unittest.mock import MagicMock

import pytest

from cfd.data.journal_openalex import JournalOpenAlexCollector


class TestJournalOpenAlexCollector:
    def _make_collector(self, responses=None):
        """Create collector with mocked HTTP client."""
        http = MagicMock()
        if responses:
            http.get.side_effect = responses
        return JournalOpenAlexCollector(http), http

    def test_fetch_journal_by_name(self):
        collector, http = self._make_collector()
        http.get.return_value = {
            "results": [{
                "id": "https://openalex.org/S100",
                "display_name": "Test Journal",
                "issn": ["1234-5678"],
                "issn_l": "1234-5678",
                "host_organization_name": "Test Publisher",
                "works_count": 500,
                "cited_by_count": 10000,
                "summary_stats": {"h_index": 30, "i10_index": 100},
                "topics": [{"display_name": "Computer Science"}],
                "counts_by_year": [],
                "type": "journal",
                "is_oa": True,
            }],
        }

        profile = collector._fetch_journal("Test Journal")
        assert profile.openalex_id == "S100"
        assert profile.display_name == "Test Journal"
        assert profile.h_index == 30
        assert profile.is_oa is True

    def test_fetch_journal_not_found(self):
        collector, http = self._make_collector()
        http.get.return_value = {"results": []}

        with pytest.raises(ValueError, match="Journal not found"):
            collector._fetch_journal("NonexistentJournal")

    def test_fetch_journal_by_issn(self):
        collector, http = self._make_collector()
        http.get.return_value = {
            "results": [{
                "id": "https://openalex.org/S200",
                "display_name": "ISSN Journal",
                "works_count": 100,
                "cited_by_count": 5000,
                "summary_stats": {},
                "topics": [],
                "counts_by_year": [],
            }],
        }

        profile = collector._fetch_journal("", issn="1234-5678")
        assert profile.openalex_id == "S200"
        # Check that filter used issn
        call_kwargs = http.get.call_args
        assert "issn:1234-5678" in str(call_kwargs)

    def test_parse_work(self):
        collector, _ = self._make_collector()
        work_data = {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1234/test",
            "title": "Test Paper",
            "publication_date": "2024-01-15",
            "cited_by_count": 5,
            "referenced_works": [
                "https://openalex.org/W100",
                "https://openalex.org/W200",
            ],
            "authorships": [{
                "author": {
                    "id": "https://openalex.org/A1",
                    "display_name": "Smith J",
                },
                "institutions": [{"display_name": "MIT"}],
                "author_position": "first",
            }],
        }

        work = collector._parse_work(work_data, "S100")
        assert work.work_id == "W123"
        assert work.cited_by_count == 5
        assert len(work.references_list) == 2
        assert work.references_list[0] == "W100"
        assert len(work.authors) == 1
        assert work.authors[0]["display_name"] == "Smith J"

    def test_parse_work_no_id(self):
        collector, _ = self._make_collector()
        assert collector._parse_work({"id": ""}, "S100") is None
        assert collector._parse_work({}, "S100") is None

    def test_parse_journal_with_apc(self):
        collector, http = self._make_collector()
        http.get.return_value = {
            "results": [{
                "id": "https://openalex.org/S300",
                "display_name": "OA Journal",
                "works_count": 200,
                "cited_by_count": 3000,
                "summary_stats": {"h_index": 15},
                "apc_usd": {"price": 2500, "currency": "USD"},
                "topics": [],
                "counts_by_year": [],
                "is_oa": True,
            }],
        }

        profile = collector._fetch_journal("OA Journal")
        assert profile.apc_usd == 2500

    def test_polite_email_param(self):
        http = MagicMock()
        http.get.return_value = {"results": []}
        collector = JournalOpenAlexCollector(http, polite_email="test@example.com")

        with pytest.raises(ValueError):
            collector._fetch_journal("Test")

        call_kwargs = http.get.call_args
        assert "test@example.com" in str(call_kwargs)
