"""Tests for journal data models."""

from datetime import date

from cfd.data.journal_models import (
    JournalCitation,
    JournalData,
    JournalProfile,
    JournalWork,
)


class TestJournalProfile:
    def test_minimal(self):
        p = JournalProfile(openalex_id="S123", display_name="Test Journal")
        assert p.openalex_id == "S123"
        assert p.display_name == "Test Journal"
        assert p.works_count == 0
        assert p.cited_by_count == 0
        assert p.h_index is None
        assert p.issn == []
        assert p.subjects == []

    def test_full_profile(self):
        p = JournalProfile(
            openalex_id="S456",
            issn=["1234-5678", "8765-4321"],
            issn_l="1234-5678",
            display_name="Nature",
            publisher="Springer Nature",
            country_code="GB",
            type="journal",
            works_count=100000,
            cited_by_count=5000000,
            h_index=500,
            is_oa=False,
            subjects=["Physics", "Chemistry"],
        )
        assert p.publisher == "Springer Nature"
        assert p.country_code == "GB"
        assert p.h_index == 500
        assert len(p.subjects) == 2


class TestJournalWork:
    def test_basic_work(self):
        w = JournalWork(
            work_id="W123",
            title="Test Paper",
            publication_date=date(2024, 1, 15),
            cited_by_count=10,
        )
        assert w.work_id == "W123"
        assert w.cited_by_count == 10
        assert w.authors == []
        assert w.references_list == []

    def test_work_with_authors(self):
        w = JournalWork(
            work_id="W456",
            authors=[
                {"author_id": "A1", "display_name": "Smith"},
                {"author_id": "A2", "display_name": "Jones"},
            ],
            references_list=["W100", "W200"],
        )
        assert len(w.authors) == 2
        assert len(w.references_list) == 2


class TestJournalCitation:
    def test_self_citation(self):
        c = JournalCitation(
            source_work_id="W1",
            target_work_id="W2",
            source_journal_id="S1",
            target_journal_id="S1",
            is_self_citation=True,
        )
        assert c.is_self_citation is True

    def test_cross_journal(self):
        c = JournalCitation(
            source_work_id="W1",
            target_work_id="W2",
            source_journal_id="S2",
            target_journal_id="S1",
            is_self_citation=False,
        )
        assert c.is_self_citation is False


class TestJournalData:
    def test_empty_data(self):
        p = JournalProfile(openalex_id="S1", display_name="Test")
        d = JournalData(profile=p)
        assert d.works == []
        assert d.citations == []
        assert d.citing_journals == {}

    def test_full_data(self):
        p = JournalProfile(openalex_id="S1", display_name="Test")
        w = JournalWork(work_id="W1", cited_by_count=5)
        c = JournalCitation(source_work_id="W2", target_work_id="W1", is_self_citation=True)
        d = JournalData(
            profile=p,
            works=[w],
            citations=[c],
            citing_journals={"S1": 3, "S2": 7},
        )
        assert len(d.works) == 1
        assert len(d.citations) == 1
        assert d.citing_journals["S2"] == 7
