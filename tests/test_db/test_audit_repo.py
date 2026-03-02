"""Tests for AuditLogRepository."""

from __future__ import annotations

from cfd.db.repositories.audit import AuditLogRepository

from .conftest import set_execute_data


class TestAuditLogRepository:
    def test_log_full_params(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = AuditLogRepository(mock_client)
        result = repo.log(
            "view_report", target_author_id=1,
            details={"key": "val"}, user_id="admin", api_key_id=5,
        )
        assert result["id"] == 1
        call_args = mock_client.table.return_value.insert.call_args[0][0]
        assert call_args["user_id"] == "admin"
        assert call_args["api_key_id"] == 5

    def test_log_minimal(self, mock_client):
        set_execute_data(mock_client, [])
        repo = AuditLogRepository(mock_client)
        result = repo.log("analyze")
        assert isinstance(result, dict)

    def test_get_by_author(self, mock_client):
        set_execute_data(mock_client, [{"action": "view_report"}])
        repo = AuditLogRepository(mock_client)
        result = repo.get_by_author(1)
        assert len(result) == 1

    def test_get_all(self, mock_client):
        set_execute_data(mock_client, [{"action": "a"}, {"action": "b"}])
        repo = AuditLogRepository(mock_client)
        result = repo.get_all(limit=10, offset=0)
        assert len(result) == 2
