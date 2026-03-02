"""Tests for audit log endpoint."""

from __future__ import annotations


class TestAuditLog:
    def test_admin_can_access(self, client_admin, mock_repos):
        mock_repos["audit"].get_all.return_value = [
            {"id": 1, "action": "view_report", "timestamp": "2024-01-01", "target_author_id": 1},
        ]
        resp = client_admin.get("/api/v1/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["action"] == "view_report"

    def test_reader_forbidden(self, client_reader):
        resp = client_reader.get("/api/v1/audit")
        assert resp.status_code == 403

    def test_analyst_forbidden(self, client_analyst):
        resp = client_analyst.get("/api/v1/audit")
        assert resp.status_code == 403

    def test_pagination_params(self, client_admin, mock_repos):
        client_admin.get("/api/v1/audit?limit=10&offset=5")
        mock_repos["audit"].get_all.assert_called_once_with(limit=10, offset=5)

    def test_default_pagination(self, client_admin, mock_repos):
        client_admin.get("/api/v1/audit")
        mock_repos["audit"].get_all.assert_called_once_with(limit=100, offset=0)
