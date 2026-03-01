"""Tests for CSV batch import with validation and deduplication."""

import textwrap
from pathlib import Path

from cfd.data.batch import load_batch_csv


class TestLoadBatchCsv:
    def test_valid_csv(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text("surname,scopus_id,orcid\nIvanenko,57200000001,0000-0002-1234-5678\n", encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.entries) == 1
        assert result.entries[0].surname == "Ivanenko"
        assert result.entries[0].scopus_id == "57200000001"
        assert result.entries[0].orcid == "0000-0002-1234-5678"
        assert not result.errors

    def test_scopus_only(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text("surname,scopus_id\nIvanenko,57200000001\n", encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.entries) == 1
        assert result.entries[0].orcid is None

    def test_orcid_only(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text("surname,orcid\nIvanenko,0000-0002-1234-5678\n", encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.entries) == 1
        assert result.entries[0].scopus_id is None

    def test_missing_surname_column(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text("name,scopus_id\nIvanenko,57200000001\n", encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.errors) > 0
        assert "surname" in result.errors[0]

    def test_missing_id_columns(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text("surname\nIvanenko\n", encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.errors) > 0
        assert "scopus_id" in result.errors[0] or "orcid" in result.errors[0]

    def test_empty_surname_row(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text("surname,scopus_id\n,57200000001\nIvanenko,57200000002\n", encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.entries) == 1
        assert "empty surname" in result.errors[0]

    def test_invalid_scopus_id(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text("surname,scopus_id\nIvanenko,123\n", encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.entries) == 0
        assert len(result.errors) == 1

    def test_invalid_orcid(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text("surname,orcid\nIvanenko,bad-orcid\n", encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.entries) == 0
        assert len(result.errors) == 1

    def test_no_id_provided(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text("surname,scopus_id,orcid\nIvanenko,,\n", encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.entries) == 0
        assert "no Scopus ID or ORCID" in result.errors[0]

    def test_deduplication(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        csv_file.write_text(
            "surname,scopus_id\nIvanenko,57200000001\nIvanenko2,57200000001\n",
            encoding="utf-8",
        )
        result = load_batch_csv(csv_file)
        assert len(result.entries) == 1
        assert result.duplicates_removed == 1
        assert len(result.warnings) == 1

    def test_file_not_found(self, tmp_path):
        result = load_batch_csv(tmp_path / "nonexistent.csv")
        assert len(result.errors) == 1
        assert "not found" in result.errors[0]

    def test_sample_batch_fixture(self):
        """Test with the actual sample batch CSV fixture."""
        fixture = Path(__file__).parent.parent / "fixtures" / "sample_batch.csv"
        result = load_batch_csv(fixture)
        assert len(result.entries) == 3
        assert result.entries[0].surname == "Ivanenko"
        assert result.entries[1].surname == "Petrenko"
        assert result.entries[2].surname == "Sydorenko"
        assert not result.errors

    def test_multiple_entries(self, tmp_path):
        csv_file = tmp_path / "authors.csv"
        content = textwrap.dedent("""\
            surname,scopus_id,orcid
            Author1,57200000001,
            Author2,,0000-0002-1234-5678
            Author3,57200000003,0000-0003-9876-5432
        """)
        csv_file.write_text(content, encoding="utf-8")
        result = load_batch_csv(csv_file)
        assert len(result.entries) == 3
        assert not result.errors
