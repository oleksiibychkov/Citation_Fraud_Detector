"""Tests for CSV export."""

import csv

from cfd.analysis.pipeline import AnalysisResult
from cfd.data.models import AuthorProfile
from cfd.export.csv_export import export_ranking_csv, export_to_csv
from cfd.graph.metrics import IndicatorResult


def _make_result(surname="Test", fraud_score=0.5, confidence="moderate", indicators=None, triggered=None):
    profile = AuthorProfile(
        surname=surname, full_name=f"{surname} Author",
        scopus_id="123", orcid="0000-0001-2345-6789",
        source_api="openalex",
    )
    return AnalysisResult(
        author_profile=profile,
        indicators=indicators or [IndicatorResult("SCR", 0.3, {})],
        fraud_score=fraud_score,
        confidence_level=confidence,
        triggered_indicators=triggered or ["SCR"],
    )


class TestExportToCsv:
    def test_creates_file(self, tmp_path):
        result = _make_result()
        output = tmp_path / "report.csv"
        export_to_csv(result, output)
        assert output.exists()

    def test_csv_structure(self, tmp_path):
        result = _make_result(indicators=[
            IndicatorResult("SCR", 0.3, {"self_citations": 5}),
            IndicatorResult("MCR", 0.1, {}),
        ], triggered=["SCR"])
        output = tmp_path / "report.csv"
        export_to_csv(result, output)

        with open(output, encoding="utf-8") as f:
            reader = list(csv.reader(f))
        # Should have header rows + empty row + column header + data rows
        non_empty = [row for row in reader if row]
        assert any("indicator_type" in row for row in non_empty)
        # Should have both indicators
        values = [row[0] for row in non_empty]
        assert "SCR" in values
        assert "MCR" in values

    def test_triggered_column(self, tmp_path):
        result = _make_result(indicators=[
            IndicatorResult("SCR", 0.3, {}),
            IndicatorResult("MCR", 0.0, {}),
        ], triggered=["SCR"])
        output = tmp_path / "report.csv"
        export_to_csv(result, output)

        with open(output, encoding="utf-8") as f:
            content = f.read()
        assert "YES" in content
        assert "NO" in content

    def test_creates_parent_dirs(self, tmp_path):
        output = tmp_path / "sub" / "dir" / "report.csv"
        export_to_csv(_make_result(), output)
        assert output.exists()

    def test_unicode_names(self, tmp_path):
        result = _make_result(surname="Іваненко")
        output = tmp_path / "report.csv"
        export_to_csv(result, output)
        with open(output, encoding="utf-8") as f:
            content = f.read()
        assert "Іваненко" in content


class TestExportRankingCsv:
    def test_ranking_sorted(self, tmp_path):
        results = [
            _make_result(surname="Low", fraud_score=0.2, confidence="normal"),
            _make_result(surname="High", fraud_score=0.8, confidence="critical"),
            _make_result(surname="Mid", fraud_score=0.5, confidence="moderate"),
        ]
        output = tmp_path / "ranking.csv"
        export_ranking_csv(results, output)

        with open(output, encoding="utf-8") as f:
            reader = list(csv.reader(f))
        # First data row (rank 1) should be "High" (highest score)
        assert reader[1][1] == "High"
        assert reader[2][1] == "Mid"
        assert reader[3][1] == "Low"
