"""Tests for compare CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cfd.cli.main import cli


@patch("cfd.db.repositories.snapshots.SnapshotRepository")
@patch("cfd.db.client.get_supabase_client")
def test_compare_no_snapshots(mock_client, mock_snap_repo):
    mock_client.return_value = MagicMock()
    mock_snap_repo.return_value.get_by_author_id.return_value = []

    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "--author-id", "1"])
    assert "no snapshots" in result.output.lower() or result.exit_code == 0


@patch("cfd.db.repositories.snapshots.SnapshotRepository")
@patch("cfd.db.client.get_supabase_client")
def test_compare_single_snapshot(mock_client, mock_snap_repo):
    mock_client.return_value = MagicMock()
    mock_snap_repo.return_value.get_by_author_id.return_value = [
        {"fraud_score": 0.5, "h_index": 10, "snapshot_date": "2024-01-01"},
    ]

    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "--author-id", "1"])
    assert "one snapshot" in result.output.lower() or result.exit_code == 0


@patch("cfd.db.repositories.snapshots.SnapshotRepository")
@patch("cfd.db.client.get_supabase_client")
def test_compare_two_snapshots(mock_client, mock_snap_repo):
    mock_client.return_value = MagicMock()
    mock_snap_repo.return_value.get_by_author_id.return_value = [
        {
            "fraud_score": 0.6,
            "h_index": 12,
            "citation_count": 200,
            "publication_count": 20,
            "snapshot_date": "2024-06-01",
            "algorithm_version": "4.0.0",
        },
        {
            "fraud_score": 0.5,
            "h_index": 10,
            "citation_count": 150,
            "publication_count": 18,
            "snapshot_date": "2024-01-01",
            "algorithm_version": "4.0.0",
        },
    ]

    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "--author-id", "1"])
    assert result.exit_code == 0


@patch("cfd.db.repositories.snapshots.SnapshotRepository")
@patch("cfd.db.client.get_supabase_client")
def test_compare_error_handling(mock_client, mock_snap_repo):
    mock_client.side_effect = Exception("DB unavailable")

    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "--author-id", "1"])
    assert result.exit_code != 0 or "error" in result.output.lower()
