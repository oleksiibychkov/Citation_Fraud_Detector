"""Tests for visualize CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cfd.analysis.pipeline import AnalysisResult
from cfd.cli.main import cli
from cfd.data.models import AuthorProfile
from cfd.graph.metrics import IndicatorResult


def _mock_result():
    return AnalysisResult(
        author_profile=AuthorProfile(
            scopus_id="57200000001",
            orcid="0000-0002-1234-5678",
            surname="Ivanenko",
            full_name="Oleksandr Ivanenko",
            institution="KNU",
            h_index=15,
            publication_count=50,
            citation_count=500,
            source_api="openalex",
        ),
        indicators=[IndicatorResult("SCR", 0.15, {})],
        fraud_score=0.12,
        confidence_level="normal",
        triggered_indicators=[],
        status="completed",
        warnings=[],
    )


class TestVisualizeCommand:
    def test_missing_id(self):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "visualize", "--author", "Ivanenko",
            "--output", "out.html",
        ])
        assert result.exit_code != 0

    @patch("cfd.cli.visualize_commands._build_figure")
    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_network_viz(self, mock_strategy, mock_pipeline, mock_fig):
        mock_pipeline.return_value.analyze.return_value = _mock_result()
        mock_strategy.return_value.collect.return_value = MagicMock()
        mock_fig.return_value = MagicMock()

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                "visualize", "--author", "Ivanenko",
                "--scopus-id", "57200000001",
                "--type", "network",
                "--output", "net.html",
            ])
            assert result.exit_code == 0
            assert "Visualization saved" in result.output

    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_analysis_failure(self, mock_strategy, mock_pipeline):
        mock_pipeline.return_value.analyze.side_effect = Exception("API fail")

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                "visualize", "--author", "Ivanenko",
                "--scopus-id", "57200000001",
                "--output", "out.html",
            ])
            assert result.exit_code != 0

    @patch("cfd.cli.visualize_commands._build_figure")
    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_collect_failure_uses_limited_data(self, mock_strategy, mock_pipeline, mock_fig):
        mock_pipeline.return_value.analyze.return_value = _mock_result()
        mock_strategy.return_value.collect.side_effect = Exception("fail")
        mock_fig.return_value = MagicMock()

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                "visualize", "--author", "Ivanenko",
                "--orcid", "0000-0002-1234-5678",
                "--output", "viz.html",
            ])
            assert result.exit_code == 0
            assert "limited data" in result.output
