"""Tests for discipline baselines module."""

from unittest.mock import MagicMock

from cfd.analysis.baselines import (
    DEFAULT_BASELINES,
    DisciplineBaseline,
    get_baseline,
    get_journal_quartile,
    normalize_by_discipline,
)


class TestGetBaseline:
    def test_known_discipline(self):
        b = get_baseline("Computer Science")
        assert b.discipline == "Computer Science"
        assert b.avg_scr == 0.12

    def test_unknown_discipline_returns_cross(self):
        b = get_baseline("Underwater Basket Weaving")
        assert b.discipline == "Cross-discipline"

    def test_none_discipline_returns_cross(self):
        b = get_baseline(None)
        assert b.discipline == "Cross-discipline"

    def test_partial_match(self):
        b = get_baseline("medicine")
        assert b.discipline == "Medicine"

    def test_all_defaults_exist(self):
        assert len(DEFAULT_BASELINES) == 5
        for _name, bl in DEFAULT_BASELINES.items():
            assert bl.avg_scr > 0
            assert bl.std_scr > 0
            assert bl.citation_half_life_years > 0

    def test_db_repo_fallback(self):
        repo = MagicMock()
        repo.get_by_discipline.return_value = {
            "discipline": "Test Discipline",
            "avg_scr": 0.20,
            "std_scr": 0.15,
        }
        b = get_baseline("Test Discipline", repo=repo)
        assert b.discipline == "Test Discipline"
        assert b.avg_scr == 0.20

    def test_db_repo_failure_falls_back(self):
        repo = MagicMock()
        repo.get_by_discipline.side_effect = Exception("DB error")
        b = get_baseline("Computer Science", repo=repo)
        assert b.discipline == "Computer Science"


class TestNormalizeByDiscipline:
    def test_at_mean(self):
        assert normalize_by_discipline(0.12, 0.12, 0.08) == 0.0

    def test_above_mean(self):
        z = normalize_by_discipline(0.20, 0.12, 0.08)
        assert abs(z - 1.0) < 1e-10

    def test_below_mean(self):
        z = normalize_by_discipline(0.04, 0.12, 0.08)
        assert abs(z - (-1.0)) < 1e-10

    def test_zero_std(self):
        assert normalize_by_discipline(0.5, 0.1, 0.0) == 0.0


class TestGetJournalQuartile:
    def test_nature_is_q1(self):
        assert get_journal_quartile("Nature", DisciplineBaseline("test", 0.1, 0.1)) == "Q1"

    def test_plos_is_q2(self):
        assert get_journal_quartile("PLOS ONE", DisciplineBaseline("test", 0.1, 0.1)) == "Q2"

    def test_unknown_defaults_q3(self):
        # Unknown journals with recognizable names default to Q3
        assert get_journal_quartile("Unknown Journal", DisciplineBaseline("test", 0.1, 0.1)) == "Q3"

    def test_none_defaults_q2(self):
        assert get_journal_quartile(None, DisciplineBaseline("test", 0.1, 0.1)) == "Q2"
