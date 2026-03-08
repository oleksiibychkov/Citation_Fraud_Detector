"""Tests for organization OpenAlex data collection."""

from datetime import date
from unittest.mock import MagicMock, call

import pytest

from cfd.data.organization_openalex import (
    AffiliatedAuthor,
    InstitutionProfile,
    OrganizationCollector,
    OrganizationData,
)


class TestInstitutionProfile:
    def test_defaults(self):
        p = InstitutionProfile(openalex_id="I1", display_name="MIT")
        assert p.openalex_id == "I1"
        assert p.works_count == 0
        assert p.country_code is None


class TestAffiliatedAuthor:
    def test_defaults(self):
        a = AffiliatedAuthor(openalex_id="A1", display_name="Smith J")
        assert a.works_in_period == 0
        assert a.scopus_indexed_in_period == 0
        assert a.works_in_period_list == []
        assert a.orcid is None

    def test_with_period_data(self):
        a = AffiliatedAuthor(
            openalex_id="A1",
            display_name="Smith J",
            orcid="0000-0001-2345-6789",
            h_index=15,
            works_in_period=5,
            scopus_indexed_in_period=3,
        )
        assert a.works_in_period == 5
        assert a.scopus_indexed_in_period == 3


class TestOrganizationData:
    def test_defaults(self):
        inst = InstitutionProfile(openalex_id="I1", display_name="MIT")
        d = OrganizationData(institution=inst)
        assert d.authors == []
        assert d.total_works_in_period == 0

    def test_with_data(self):
        inst = InstitutionProfile(openalex_id="I1", display_name="MIT")
        author = AffiliatedAuthor(
            openalex_id="A1",
            display_name="Smith",
            works_in_period=10,
            scopus_indexed_in_period=7,
        )
        d = OrganizationData(
            institution=inst,
            authors=[author],
            period_from=date(2024, 1, 1),
            period_to=date(2024, 12, 31),
            total_works_in_period=10,
            total_scopus_indexed=7,
        )
        assert len(d.authors) == 1
        assert d.total_scopus_indexed == 7


class TestOrganizationCollector:
    def _make_collector(self):
        http = MagicMock()
        return OrganizationCollector(http), http

    def test_fetch_institution_by_name(self):
        collector, http = self._make_collector()
        http.get.return_value = {
            "results": [{
                "id": "https://openalex.org/I123",
                "display_name": "MIT",
                "ids": {"ror": "https://ror.org/042nb2s44"},
                "country_code": "US",
                "type": "education",
                "homepage_url": "https://mit.edu",
                "works_count": 500000,
                "cited_by_count": 10000000,
                "summary_stats": {},
            }],
        }

        inst = collector.fetch_institution("MIT")
        assert inst.openalex_id == "I123"
        assert inst.display_name == "MIT"
        assert inst.country_code == "US"
        assert inst.works_count == 500000

    def test_fetch_institution_not_found(self):
        collector, http = self._make_collector()
        http.get.return_value = {"results": []}

        with pytest.raises(ValueError, match="Institution not found"):
            collector.fetch_institution("NonexistentUniversity")

    def test_fetch_institution_by_ror(self):
        collector, http = self._make_collector()
        http.get.return_value = {
            "id": "https://openalex.org/I456",
            "display_name": "Oxford",
            "ids": {},
            "country_code": "GB",
            "works_count": 300000,
            "cited_by_count": 8000000,
            "summary_stats": {},
        }

        inst = collector.fetch_institution("", ror="042nb2s44")
        assert inst.openalex_id == "I456"
        # Check that the ROR-specific URL was called
        call_args = http.get.call_args
        assert "ror:" in call_args[0][0]

    def test_parse_author(self):
        collector, _ = self._make_collector()
        data = {
            "id": "https://openalex.org/A100",
            "display_name": "John Smith",
            "ids": {
                "orcid": "https://orcid.org/0000-0001-2345-6789",
                "scopus": "https://www.scopus.com/authid/detail.uri?authorId=123456",
            },
            "summary_stats": {"h_index": 25},
            "works_count": 100,
            "cited_by_count": 5000,
            "last_known_institutions": [
                {"display_name": "MIT"},
            ],
        }

        author = collector._parse_author(data)
        assert author.openalex_id == "A100"
        assert author.display_name == "John Smith"
        assert author.orcid == "0000-0001-2345-6789"
        assert author.scopus_id == "123456"
        assert author.h_index == 25
        assert author.last_known_institution == "MIT"

    def test_parse_author_no_id(self):
        collector, _ = self._make_collector()
        assert collector._parse_author({"id": ""}) is None
        assert collector._parse_author({}) is None

    def test_fetch_affiliated_authors_pagination(self):
        collector, http = self._make_collector()

        # First page
        page1 = {
            "results": [
                {"id": f"https://openalex.org/A{i}", "display_name": f"Author {i}",
                 "ids": {}, "summary_stats": {}, "works_count": 10, "cited_by_count": 50}
                for i in range(3)
            ],
            "meta": {"next_cursor": "cursor2"},
        }
        # Second page (empty — end of results)
        page2 = {"results": [], "meta": {}}

        http.get.side_effect = [page1, page2]

        authors = collector.fetch_affiliated_authors("I123")
        assert len(authors) == 3
        assert authors[0].openalex_id == "A0"

    def test_fetch_author_works_in_period(self):
        collector, http = self._make_collector()
        http.get.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.1234/test",
                    "title": "Test Paper",
                    "publication_date": "2024-06-15",
                    "primary_location": {
                        "source": {
                            "display_name": "Nature",
                            "type": "journal",
                            "issn_l": "0028-0836",
                        },
                    },
                    "type": "article",
                },
                {
                    "id": "https://openalex.org/W2",
                    "title": "Preprint",
                    "publication_date": "2024-03-01",
                    "primary_location": {
                        "source": {
                            "display_name": "arXiv",
                            "type": "repository",
                        },
                    },
                    "type": "article",
                },
            ],
            "meta": {},
        }

        author = AffiliatedAuthor(openalex_id="A1", display_name="Test Author")
        collector.fetch_author_works_in_period(
            author, date(2024, 1, 1), date(2024, 12, 31),
        )

        assert author.works_in_period == 2
        assert author.scopus_indexed_in_period == 1  # Only Nature has ISSN
        assert len(author.works_in_period_list) == 2
        assert author.works_in_period_list[0]["journal"] == "Nature"
        assert author.works_in_period_list[0]["is_scopus_indexed"] is True
        assert author.works_in_period_list[1]["is_scopus_indexed"] is False

    def test_fetch_author_works_api_error(self):
        collector, http = self._make_collector()
        http.get.side_effect = Exception("API error")

        author = AffiliatedAuthor(openalex_id="A1", display_name="Test")
        collector.fetch_author_works_in_period(
            author, date(2024, 1, 1), date(2024, 12, 31),
        )
        assert author.works_in_period == 0

    def test_collect_organization_full(self):
        collector, http = self._make_collector()

        # Institution search response
        inst_response = {
            "results": [{
                "id": "https://openalex.org/I100",
                "display_name": "Test University",
                "ids": {},
                "country_code": "UA",
                "works_count": 1000,
                "cited_by_count": 50000,
                "summary_stats": {},
            }],
        }

        # Authors response
        authors_response = {
            "results": [{
                "id": "https://openalex.org/A1",
                "display_name": "Prof Test",
                "ids": {"orcid": "https://orcid.org/0000-0001-0000-0001"},
                "summary_stats": {"h_index": 10},
                "works_count": 50,
                "cited_by_count": 1000,
            }],
            "meta": {},
        }

        # Works response
        works_response = {
            "results": [{
                "id": "https://openalex.org/W1",
                "title": "Paper 1",
                "publication_date": "2024-06-01",
                "primary_location": {
                    "source": {"display_name": "J. Science", "type": "journal", "issn_l": "1234-5678"},
                },
                "type": "article",
            }],
            "meta": {},
        }

        http.get.side_effect = [inst_response, authors_response, works_response]

        result = collector.collect_organization(
            "Test University",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
            max_authors=10,
        )

        assert result.institution.display_name == "Test University"
        assert len(result.authors) == 1
        assert result.authors[0].works_in_period == 1
        assert result.authors[0].scopus_indexed_in_period == 1
        assert result.total_works_in_period == 1
        assert result.total_scopus_indexed == 1

    def test_polite_email(self):
        http = MagicMock()
        http.get.return_value = {"results": []}
        collector = OrganizationCollector(http, polite_email="admin@uni.edu")

        with pytest.raises(ValueError):
            collector.fetch_institution("Test")

        call_kwargs = http.get.call_args
        assert "admin@uni.edu" in str(call_kwargs)
