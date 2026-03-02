"""Tests for watchlist reanalyze and set-sensitivity CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cfd.cli.main import cli


class TestReanalyzeCommand:
    """Tests for `cfd watchlist reanalyze`."""

    def test_reanalyze_without_all_flag(self):
        """Running reanalyze without --all shows an error message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["watchlist", "reanalyze"])
        assert "Use --all" in result.output

    @patch("cfd.notifications.dispatcher.dispatch_score_change")
    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    @patch("cfd.cli.main._build_strategy")
    @patch("cfd.db.repositories.snapshots.SnapshotRepository")
    @patch("cfd.db.repositories.fraud_scores.FraudScoreRepository")
    @patch("cfd.db.repositories.indicators.IndicatorRepository")
    @patch("cfd.db.repositories.citations.CitationRepository")
    @patch("cfd.db.repositories.publications.PublicationRepository")
    @patch("cfd.db.repositories.authors.AuthorRepository")
    @patch("cfd.db.repositories.watchlist.WatchlistRepository")
    @patch("cfd.db.client.get_supabase_client")
    def test_reanalyze_empty_watchlist(
        self, mock_client, mock_wl_repo, mock_author_repo,
        mock_pub_repo, mock_cit_repo, mock_ind_repo, mock_score_repo,
        mock_snap_repo, mock_build_strategy, mock_pipeline, mock_dispatch,
    ):
        """Reanalyze with --all on empty watchlist shows 'no active' message."""
        mock_client.return_value = MagicMock()
        mock_wl_repo.return_value.get_active.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, ["watchlist", "reanalyze", "--all"])
        assert "No active" in result.output or "no active" in result.output.lower()

    @patch("cfd.notifications.dispatcher.dispatch_score_change")
    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    @patch("cfd.cli.main._build_strategy")
    @patch("cfd.db.repositories.snapshots.SnapshotRepository")
    @patch("cfd.db.repositories.fraud_scores.FraudScoreRepository")
    @patch("cfd.db.repositories.indicators.IndicatorRepository")
    @patch("cfd.db.repositories.citations.CitationRepository")
    @patch("cfd.db.repositories.publications.PublicationRepository")
    @patch("cfd.db.repositories.authors.AuthorRepository")
    @patch("cfd.db.repositories.watchlist.WatchlistRepository")
    @patch("cfd.db.client.get_supabase_client")
    def test_reanalyze_success(
        self, mock_client, mock_wl_repo, mock_author_repo,
        mock_pub_repo, mock_cit_repo, mock_ind_repo, mock_score_repo,
        mock_snap_repo, mock_build_strategy, mock_pipeline_cls, mock_dispatch,
    ):
        """Reanalyze successfully processes a watchlist entry."""
        mock_client.return_value = MagicMock()
        mock_wl_repo.return_value.get_active.return_value = [
            {"author_id": 1, "sensitivity_overrides": None},
        ]
        mock_author_repo.return_value.get_by_id.return_value = {
            "id": 1, "surname": "Ivanenko", "full_name": "Oleksandr Ivanenko",
            "scopus_id": "57200000001", "orcid": "0000-0002-1234-5678",
        }
        mock_score_repo.return_value.get_latest_by_author.return_value = {"score": 0.30}

        mock_result = MagicMock()
        mock_result.fraud_score = 0.55
        mock_result.confidence_level = "normal"
        mock_result.status = "completed"
        mock_result.indicators = []
        mock_pipeline_cls.return_value.analyze.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["watchlist", "reanalyze", "--all"])

        assert result.exit_code == 0
        assert "Ivanenko" in result.output
        assert "0.5500" in result.output
        mock_dispatch.assert_called_once()
        mock_snap_repo.return_value.save.assert_called_once()

    @patch("cfd.notifications.dispatcher.dispatch_score_change")
    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    @patch("cfd.cli.main._build_strategy")
    @patch("cfd.db.repositories.snapshots.SnapshotRepository")
    @patch("cfd.db.repositories.fraud_scores.FraudScoreRepository")
    @patch("cfd.db.repositories.indicators.IndicatorRepository")
    @patch("cfd.db.repositories.citations.CitationRepository")
    @patch("cfd.db.repositories.publications.PublicationRepository")
    @patch("cfd.db.repositories.authors.AuthorRepository")
    @patch("cfd.db.repositories.watchlist.WatchlistRepository")
    @patch("cfd.db.client.get_supabase_client")
    def test_reanalyze_author_not_found_skips(
        self, mock_client, mock_wl_repo, mock_author_repo,
        mock_pub_repo, mock_cit_repo, mock_ind_repo, mock_score_repo,
        mock_snap_repo, mock_build_strategy, mock_pipeline_cls, mock_dispatch,
    ):
        """Reanalyze skips entries whose author is not found in the DB."""
        mock_client.return_value = MagicMock()
        mock_wl_repo.return_value.get_active.return_value = [
            {"author_id": 999, "sensitivity_overrides": None},
        ]
        mock_author_repo.return_value.get_by_id.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, ["watchlist", "reanalyze", "--all"])
        assert "skipping" in result.output.lower() or "not found" in result.output.lower()
        mock_pipeline_cls.return_value.analyze.assert_not_called()

    @patch("cfd.notifications.dispatcher.dispatch_score_change")
    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    @patch("cfd.cli.main._build_strategy")
    @patch("cfd.db.repositories.snapshots.SnapshotRepository")
    @patch("cfd.db.repositories.fraud_scores.FraudScoreRepository")
    @patch("cfd.db.repositories.indicators.IndicatorRepository")
    @patch("cfd.db.repositories.citations.CitationRepository")
    @patch("cfd.db.repositories.publications.PublicationRepository")
    @patch("cfd.db.repositories.authors.AuthorRepository")
    @patch("cfd.db.repositories.watchlist.WatchlistRepository")
    @patch("cfd.db.client.get_supabase_client")
    def test_reanalyze_pipeline_error_handled(
        self, mock_client, mock_wl_repo, mock_author_repo,
        mock_pub_repo, mock_cit_repo, mock_ind_repo, mock_score_repo,
        mock_snap_repo, mock_build_strategy, mock_pipeline_cls, mock_dispatch,
    ):
        """Pipeline error for one author is caught and displayed, not fatal."""
        mock_client.return_value = MagicMock()
        mock_wl_repo.return_value.get_active.return_value = [
            {"author_id": 1, "sensitivity_overrides": None},
        ]
        mock_author_repo.return_value.get_by_id.return_value = {
            "id": 1, "surname": "Kovalenko", "full_name": "A. Kovalenko",
            "scopus_id": "111", "orcid": None,
        }
        mock_score_repo.return_value.get_latest_by_author.return_value = None
        mock_pipeline_cls.return_value.analyze.side_effect = RuntimeError("API timeout")

        runner = CliRunner()
        result = runner.invoke(cli, ["watchlist", "reanalyze", "--all"])
        assert result.exit_code == 0
        assert "API timeout" in result.output


class TestSetSensitivityCommand:
    """Tests for `cfd watchlist set-sensitivity`."""

    @patch("cfd.db.repositories.watchlist.WatchlistRepository")
    @patch("cfd.db.client.get_supabase_client")
    def test_set_sensitivity_success(self, mock_client, mock_wl_repo):
        """Successfully sets sensitivity overrides for a watchlist author."""
        mock_client.return_value = MagicMock()
        mock_wl_repo.return_value.set_sensitivity_overrides.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, [
            "watchlist", "set-sensitivity",
            "--author-id", "42",
            "--overrides", '{"scr_warn_threshold": 0.30}',
        ])

        assert "overrides set" in result.output.lower() or "Sensitivity" in result.output
        mock_wl_repo.return_value.set_sensitivity_overrides.assert_called_once_with(
            42, {"scr_warn_threshold": 0.30},
        )

    def test_set_sensitivity_invalid_json(self):
        """Invalid JSON in --overrides shows an error."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "watchlist", "set-sensitivity",
            "--author-id", "42",
            "--overrides", "not-valid-json",
        ])
        assert "Invalid JSON" in result.output

    @patch("cfd.db.repositories.watchlist.WatchlistRepository")
    @patch("cfd.db.client.get_supabase_client")
    def test_set_sensitivity_no_entry(self, mock_client, mock_wl_repo):
        """Returns warning when no watchlist entry exists for the author."""
        mock_client.return_value = MagicMock()
        mock_wl_repo.return_value.set_sensitivity_overrides.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, [
            "watchlist", "set-sensitivity",
            "--author-id", "999",
            "--overrides", '{"scr_warn_threshold": 0.20}',
        ])
        assert "No watchlist entry" in result.output or "not found" in result.output.lower()
