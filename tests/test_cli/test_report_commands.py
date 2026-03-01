"""Tests for report CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cfd.cli.main import cli


@patch("cfd.cli.main._build_pipeline")
@patch("cfd.cli.main._build_strategy")
def test_report_missing_id(mock_strategy, mock_pipeline):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["report", "--author", "Test", "--format", "json", "--output", "out.json"]
    )
    assert result.exit_code != 0 or "required" in result.output.lower()


@patch("cfd.export.json_export.export_to_json")
@patch("cfd.cli.main._build_pipeline")
@patch("cfd.cli.main._build_strategy")
def test_report_json_success(mock_strategy, mock_pipeline, mock_export):
    mock_result = MagicMock()
    mock_result.author_profile = {"name": "Test", "scopus_id": "123"}
    mock_result.fraud_score = 0.5
    mock_result.confidence_level = "moderate"
    mock_result.algorithm_version = "4.0.0"
    mock_result.indicators = []
    mock_result.triggered_theorems = []

    mock_pipeline.return_value.analyze.return_value = mock_result

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "report",
                "--author", "Test",
                "--scopus-id", "12345",
                "--format", "json",
                "--output", "report.json",
            ],
        )
        assert result.exit_code == 0


@patch("cfd.cli.main._build_pipeline")
@patch("cfd.cli.main._build_strategy")
def test_report_analysis_failure(mock_strategy, mock_pipeline):
    mock_pipeline.return_value.analyze.side_effect = Exception("API error")

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "report",
                "--author", "Test",
                "--scopus-id", "12345",
                "--format", "json",
                "--output", "report.json",
            ],
        )
        assert result.exit_code != 0


@patch("cfd.export.csv_export.export_to_csv")
@patch("cfd.cli.main._build_pipeline")
@patch("cfd.cli.main._build_strategy")
def test_report_csv_format(mock_strategy, mock_pipeline, mock_export):
    mock_result = MagicMock()
    mock_result.author_profile = {"name": "Test", "scopus_id": "123"}
    mock_result.fraud_score = 0.3
    mock_result.confidence_level = "low"
    mock_result.algorithm_version = "4.0.0"
    mock_result.indicators = []
    mock_result.triggered_theorems = []

    mock_pipeline.return_value.analyze.return_value = mock_result

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "report",
                "--author", "Test",
                "--scopus-id", "12345",
                "--format", "csv",
                "--output", "report.csv",
            ],
        )
        assert result.exit_code == 0
