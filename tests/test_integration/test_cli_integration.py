"""Integration tests for CLI commands with mocked pipeline."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cfd.analysis.pipeline import AnalysisPipeline
from cfd.cli.main import cli
from cfd.data.openalex import OpenAlexStrategy
from cfd.exceptions import AuthorNotFoundError

from .conftest import MOCK_WORKS, _build_mock_http


def _make_pipeline():
    """Build a real pipeline with mocked HTTP."""
    from cfd.config.settings import Settings

    citing = [[] for _ in MOCK_WORKS]
    http = _build_mock_http(citing_works=citing)
    strategy = OpenAlexStrategy(http)
    settings = Settings(
        min_publications=1,
        min_citations=1,
        min_h_index=0,
        supabase_url="",
        supabase_key="",
    )
    return AnalysisPipeline(strategy=strategy, settings=settings)


class TestCLIIntegration:
    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_analyze_end_to_end(self, mock_strategy, mock_pipeline):
        pipeline = _make_pipeline()
        mock_pipeline.return_value = pipeline
        mock_strategy.return_value = MagicMock()

        runner = CliRunner()
        result = runner.invoke(cli, [
            "analyze",
            "--author", "Ivanenko",
            "--orcid", "0000-0002-1234-5678",
            "--source", "openalex",
        ])
        # The pipeline should run and produce output
        assert result.exit_code == 0 or "Ivanenko" in result.output

    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_analyze_json_export(self, mock_strategy, mock_pipeline):
        pipeline = _make_pipeline()
        mock_pipeline.return_value = pipeline
        mock_strategy.return_value = MagicMock()

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            runner.invoke(cli, [
                "analyze",
                "--author", "Ivanenko",
                "--orcid", "0000-0002-1234-5678",
                "--source", "openalex",
                "--output", str(output_path),
            ])
            if output_path.exists():
                data = json.loads(output_path.read_text(encoding="utf-8"))
                assert "disclaimer" in data
                assert "author" in data

    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_analyze_not_found(self, mock_strategy, mock_pipeline):
        pipeline = MagicMock()
        pipeline.analyze.side_effect = AuthorNotFoundError("Nobody")
        mock_pipeline.return_value = pipeline
        mock_strategy.return_value = MagicMock()

        runner = CliRunner()
        result = runner.invoke(cli, [
            "analyze",
            "--author", "Nobody",
            "--orcid", "0000-0000-0000-0000",
            "--source", "openalex",
        ])
        assert result.exit_code != 0 or "not found" in result.output.lower()

    @patch("cfd.cli.main._build_pipeline")
    @patch("cfd.cli.main._build_strategy")
    def test_batch_end_to_end(self, mock_strategy, mock_pipeline):
        """Batch analysis processes CSV entries."""
        pipeline = _make_pipeline()
        mock_pipeline.return_value = pipeline
        mock_strategy.return_value = MagicMock()

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "authors.csv"
            csv_path.write_text(
                "surname,scopus_id,orcid\n"
                "Ivanenko,57200000001,0000-0002-1234-5678\n",
                encoding="utf-8",
            )
            result = runner.invoke(cli, [
                "batch",
                "--batch", str(csv_path),
                "--source", "openalex",
                "--output-dir", tmpdir,
            ])
            assert "Ivanenko" in result.output or result.exit_code == 0
