"""Tests for HTML export."""

from cfd.analysis.pipeline import AnalysisResult
from cfd.data.models import AuthorProfile
from cfd.export.html_export import export_to_html
from cfd.graph.metrics import IndicatorResult


def _make_result(**overrides):
    profile = AuthorProfile(
        surname="Test", full_name="Test Author",
        scopus_id="123", source_api="openalex",
    )
    defaults = {
        "author_profile": profile,
        "indicators": [IndicatorResult("SCR", 0.3, {})],
        "fraud_score": 0.5,
        "confidence_level": "moderate",
        "triggered_indicators": ["SCR"],
    }
    defaults.update(overrides)
    return AnalysisResult(**defaults)


class TestExportToHtml:
    def test_creates_file(self, tmp_path):
        output = tmp_path / "report.html"
        export_to_html(_make_result(), output)
        assert output.exists()

    def test_html_structure(self, tmp_path):
        output = tmp_path / "report.html"
        export_to_html(_make_result(), output)
        content = output.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Test Author" in content
        assert "SCR" in content

    def test_localization_ua(self, tmp_path):
        output = tmp_path / "report_ua.html"
        export_to_html(_make_result(), output, lang="ua")
        content = output.read_text(encoding="utf-8")
        assert "Індикатори" in content

    def test_localization_en(self, tmp_path):
        output = tmp_path / "report_en.html"
        export_to_html(_make_result(), output, lang="en")
        content = output.read_text(encoding="utf-8")
        assert "Indicators" in content

    def test_confidence_badge(self, tmp_path):
        output = tmp_path / "report.html"
        export_to_html(_make_result(confidence_level="critical"), output)
        content = output.read_text(encoding="utf-8")
        assert "critical" in content

    def test_without_figures(self, tmp_path):
        output = tmp_path / "report.html"
        export_to_html(_make_result(), output, figures=None)
        assert output.exists()
