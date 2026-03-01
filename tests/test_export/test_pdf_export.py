"""Tests for PDF export."""

from cfd.analysis.pipeline import AnalysisResult
from cfd.data.models import AuthorProfile
from cfd.export.pdf_export import export_antiranking_pdf, export_to_pdf
from cfd.graph.metrics import IndicatorResult


def _make_result(surname="Test", fraud_score=0.5, confidence="moderate"):
    profile = AuthorProfile(
        surname=surname, full_name=f"{surname} Author",
        scopus_id="123", source_api="openalex",
    )
    return AnalysisResult(
        author_profile=profile,
        indicators=[IndicatorResult("SCR", 0.3, {}), IndicatorResult("MCR", 0.1, {})],
        fraud_score=fraud_score,
        confidence_level=confidence,
        triggered_indicators=["SCR"],
    )


class TestExportToPdf:
    def test_creates_file(self, tmp_path):
        output = tmp_path / "report.pdf"
        export_to_pdf(_make_result(), output)
        assert output.exists()
        assert output.stat().st_size > 0

    def test_pdf_is_valid(self, tmp_path):
        output = tmp_path / "report.pdf"
        export_to_pdf(_make_result(), output)
        # PDF files start with %PDF
        with open(output, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_creates_parent_dirs(self, tmp_path):
        output = tmp_path / "sub" / "dir" / "report.pdf"
        export_to_pdf(_make_result(), output)
        assert output.exists()

    def test_without_figures(self, tmp_path):
        output = tmp_path / "report.pdf"
        export_to_pdf(_make_result(), output, figures=None)
        assert output.exists()

    def test_localization(self, tmp_path):
        output_ua = tmp_path / "report_ua.pdf"
        output_en = tmp_path / "report_en.pdf"
        export_to_pdf(_make_result(), output_ua, lang="ua")
        export_to_pdf(_make_result(), output_en, lang="en")
        assert output_ua.exists()
        assert output_en.exists()


class TestExportAntirankingPdf:
    def test_creates_file(self, tmp_path):
        results = [
            _make_result("Author1", 0.8, "critical"),
            _make_result("Author2", 0.3, "low"),
        ]
        output = tmp_path / "antiranking.pdf"
        export_antiranking_pdf(results, output)
        assert output.exists()
        assert output.stat().st_size > 0
