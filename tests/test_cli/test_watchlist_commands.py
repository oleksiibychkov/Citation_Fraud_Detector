"""Tests for watchlist CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cfd.cli.main import cli


@patch("cfd.db.client.get_supabase_client")
def test_watchlist_add_no_id(mock_client):
    runner = CliRunner()
    result = runner.invoke(cli, ["watchlist", "add"])
    assert "required" in result.output.lower() or result.exit_code != 0


@patch("cfd.db.repositories.watchlist.WatchlistRepository")
@patch("cfd.db.repositories.authors.AuthorRepository")
@patch("cfd.db.client.get_supabase_client")
def test_watchlist_add_success(mock_client, mock_author_repo, mock_wl_repo):
    mock_client.return_value = MagicMock()
    mock_author_repo.return_value.get_by_scopus_id.return_value = {"id": 1}
    mock_wl_repo.return_value.add.return_value = {}

    runner = CliRunner()
    result = runner.invoke(cli, ["watchlist", "add", "--scopus-id", "12345"])
    assert result.exit_code == 0


@patch("cfd.db.repositories.watchlist.WatchlistRepository")
@patch("cfd.db.repositories.authors.AuthorRepository")
@patch("cfd.db.client.get_supabase_client")
def test_watchlist_add_author_not_found(mock_client, mock_author_repo, mock_wl_repo):
    mock_client.return_value = MagicMock()
    mock_author_repo.return_value.get_by_scopus_id.return_value = None

    runner = CliRunner()
    result = runner.invoke(cli, ["watchlist", "add", "--scopus-id", "99999"])
    assert "not found" in result.output.lower()


@patch("cfd.db.repositories.watchlist.WatchlistRepository")
@patch("cfd.db.client.get_supabase_client")
def test_watchlist_list_empty(mock_client, mock_wl_repo):
    mock_client.return_value = MagicMock()
    mock_wl_repo.return_value.get_active.return_value = []

    runner = CliRunner()
    result = runner.invoke(cli, ["watchlist", "list"])
    assert "empty" in result.output.lower()


@patch("cfd.db.repositories.watchlist.WatchlistRepository")
@patch("cfd.db.client.get_supabase_client")
def test_watchlist_list_with_entries(mock_client, mock_wl_repo):
    mock_client.return_value = MagicMock()
    mock_wl_repo.return_value.get_active.return_value = [
        {"author_id": 1, "reason": "suspicious", "created_at": "2024-01-01", "notes": None},
    ]

    runner = CliRunner()
    result = runner.invoke(cli, ["watchlist", "list"])
    assert result.exit_code == 0


@patch("cfd.db.repositories.watchlist.WatchlistRepository")
@patch("cfd.db.repositories.authors.AuthorRepository")
@patch("cfd.db.client.get_supabase_client")
def test_watchlist_remove(mock_client, mock_author_repo, mock_wl_repo):
    mock_client.return_value = MagicMock()
    mock_author_repo.return_value.get_by_scopus_id.return_value = {"id": 1}

    runner = CliRunner()
    result = runner.invoke(cli, ["watchlist", "remove", "--scopus-id", "12345"])
    assert result.exit_code == 0
