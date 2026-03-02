"""Tests for incremental analysis."""

from __future__ import annotations

from unittest.mock import MagicMock

from cfd.analysis.incremental import check_what_changed


class TestCheckWhatChanged:
    def test_new_author(self):
        author_repo = MagicMock()
        pub_repo = MagicMock()
        author_repo.get_by_id.return_value = None

        result = check_what_changed(999, author_repo, pub_repo)
        assert result == {"is_new": True}
        pub_repo.get_count_by_author_id.assert_not_called()

    def test_existing_author(self):
        author_repo = MagicMock()
        pub_repo = MagicMock()
        author_repo.get_by_id.return_value = {
            "updated_at": "2024-01-15T12:00:00",
            "citation_count": 200,
            "h_index": 12,
        }
        pub_repo.get_count_by_author_id.return_value = 30

        result = check_what_changed(1, author_repo, pub_repo)
        assert result["is_new"] is False
        assert result["stored_publication_count"] == 30
        assert result["stored_citation_count"] == 200
        assert result["stored_h_index"] == 12
        assert result["last_updated"] == "2024-01-15T12:00:00"

    def test_existing_no_optional_fields(self):
        author_repo = MagicMock()
        pub_repo = MagicMock()
        author_repo.get_by_id.return_value = {"updated_at": None}
        pub_repo.get_count_by_author_id.return_value = 0

        result = check_what_changed(1, author_repo, pub_repo)
        assert result["is_new"] is False
        assert result["stored_citation_count"] == 0
        assert result["stored_h_index"] == 0
        assert result["last_updated"] is None

    def test_last_updated_populated(self):
        author_repo = MagicMock()
        pub_repo = MagicMock()
        ts = "2025-06-01T09:30:00"
        author_repo.get_by_id.return_value = {"updated_at": ts}
        pub_repo.get_count_by_author_id.return_value = 5

        result = check_what_changed(42, author_repo, pub_repo)
        assert result["last_updated"] == ts
