"""Tests for CLI commands using Click CliRunner."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cfd.analysis.pipeline import AnalysisResult
from cfd.cli.main import cli
from cfd.data.models import AuthorProfile
from cfd.graph.metrics import IndicatorResult


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_result():
    return AnalysisResult(
        author_profile=AuthorProfile(
            scopus_id="57200000001",
            orcid="0000-0002-1234-5678",
            surname="Ivanenko",
            full_name="Oleksandr Ivanenko",
            institution="Kyiv National University",
            h_index=15,
            publication_count=50,
            citation_count=500,
            source_api="openalex",
        ),
        indicators=[
            IndicatorResult("SCR", 0.15, {"self_citations": 3, "total_citations": 20}),
            IndicatorResult("MCR", 0.05, {"status": "ok"}),
            IndicatorResult("CB", 0.20, {"max_source_count": 4, "total_incoming": 20}),
            IndicatorResult("TA", 0.10, {"max_z_score": 1.5}),
            IndicatorResult("HTA", 0.08, {"max_z_score": 1.0}),
        ],
        fraud_score=0.12,
        confidence_level="normal",
        triggered_indicators=[],
        status="completed",
        warnings=[],
    )


class TestAnalyzeCommand:
    def test_missing_id(self, runner):
        result = runner.invoke(cli, ["analyze", "--author", "Ivanenko"])
        assert result.exit_code != 0

    def test_invalid_scopus_id(self, runner):
        result = runner.invoke(cli, ["analyze", "--author", "Ivanenko", "--scopus-id", "abc"])
        assert result.exit_code != 0

    def test_invalid_orcid(self, runner):
        result = runner.invoke(cli, ["analyze", "--author", "Ivanenko", "--orcid", "bad"])
        assert result.exit_code != 0

    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_successful_analysis(self, mock_strategy, mock_pipeline, runner, mock_result):
        mock_pipeline.return_value.analyze.return_value = mock_result
        result = runner.invoke(cli, [
            "analyze", "--author", "Ivanenko",
            "--scopus-id", "57200000001", "--source", "openalex",
        ])
        assert result.exit_code == 0
        assert "Ivanenko" in result.output

    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_with_json_output(self, mock_strategy, mock_pipeline, runner, mock_result, tmp_path):
        mock_pipeline.return_value.analyze.return_value = mock_result
        output_file = tmp_path / "report.json"
        result = runner.invoke(cli, [
            "analyze", "--author", "Ivanenko",
            "--scopus-id", "57200000001",
            "--output", str(output_file),
        ])
        assert result.exit_code == 0
        assert output_file.exists()

    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_author_not_found(self, mock_strategy, mock_pipeline, runner):
        from cfd.exceptions import AuthorNotFoundError
        mock_pipeline.return_value.analyze.side_effect = AuthorNotFoundError("Not found")
        result = runner.invoke(cli, [
            "analyze", "--author", "Unknown",
            "--orcid", "0000-0002-1234-5678",
        ])
        assert result.exit_code != 0


class TestBatchCommand:
    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_batch_with_fixture(self, mock_strategy, mock_pipeline, runner, mock_result, tmp_path):
        mock_pipeline.return_value.analyze.return_value = mock_result
        from pathlib import Path
        fixture = Path(__file__).parent.parent / "fixtures" / "sample_batch.csv"

        output_dir = tmp_path / "reports"
        result = runner.invoke(cli, [
            "batch", "--batch", str(fixture),
            "--output-dir", str(output_dir),
        ])
        assert result.exit_code == 0
        assert mock_pipeline.return_value.analyze.call_count == 3

    def test_batch_missing_file(self, runner):
        result = runner.invoke(cli, ["batch", "--batch", "nonexistent.csv"])
        assert result.exit_code != 0


class TestCLIOptions:
    def test_language_option(self, runner):
        result = runner.invoke(cli, ["--lang", "en", "--help"])
        assert result.exit_code == 0

    def test_verbose_flag(self, runner):
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Citation Fraud Detector" in result.output
