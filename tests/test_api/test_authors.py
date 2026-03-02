"""Tests for author analysis endpoints."""

from __future__ import annotations


class TestGetReport:
    def test_report_success(self, client_reader, mock_repos):
        resp = client_reader.get("/api/v1/author/1/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["author"]["surname"] == "Ivanenko"
        assert data["analysis"]["fraud_score"] == 0.42
        assert data["analysis"]["confidence_level"] == "moderate"
        assert "SCR" in data["analysis"]["triggered_indicators"]
        assert len(data["indicators"]) == 2

    def test_report_404(self, client_reader, mock_repos):
        mock_repos["author"].get_by_id.return_value = None
        resp = client_reader.get("/api/v1/author/999/report")
        assert resp.status_code == 404

    def test_report_no_score(self, client_reader, mock_repos):
        mock_repos["fraud_score"].get_latest_by_author.return_value = None
        resp = client_reader.get("/api/v1/author/1/report")
        assert resp.status_code == 200
        assert resp.json()["analysis"]["fraud_score"] == 0.0

    def test_report_logs_audit(self, client_reader, mock_repos):
        client_reader.get("/api/v1/author/1/report")
        mock_repos["audit"].log.assert_called_once()
        call_args = mock_repos["audit"].log.call_args
        assert call_args[0][0] == "view_report"


class TestGetScore:
    def test_score_success(self, client_reader, mock_repos):
        resp = client_reader.get("/api/v1/author/1/score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["fraud_score"] == 0.42
        assert data["confidence_level"] == "moderate"
        assert data["algorithm_version"] != ""

    def test_score_404(self, client_reader, mock_repos):
        mock_repos["author"].get_by_id.return_value = None
        resp = client_reader.get("/api/v1/author/999/score")
        assert resp.status_code == 404

    def test_score_no_data(self, client_reader, mock_repos):
        mock_repos["fraud_score"].get_latest_by_author.return_value = None
        resp = client_reader.get("/api/v1/author/1/score")
        assert resp.status_code == 200
        assert resp.json()["fraud_score"] == 0.0


class TestGetIndicators:
    def test_indicators_success(self, client_reader, mock_repos):
        resp = client_reader.get("/api/v1/author/1/indicators")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["indicators"]) == 2
        assert data["indicators"][0]["type"] == "SCR"
        assert data["indicators"][0]["value"] == 0.65

    def test_indicators_404(self, client_reader, mock_repos):
        mock_repos["author"].get_by_id.return_value = None
        resp = client_reader.get("/api/v1/author/999/indicators")
        assert resp.status_code == 404

    def test_indicators_empty(self, client_reader, mock_repos):
        mock_repos["indicator"].get_by_author_id.return_value = []
        resp = client_reader.get("/api/v1/author/1/indicators")
        assert resp.status_code == 200
        assert resp.json()["indicators"] == []


class TestGetGraph:
    def test_graph_success(self, client_reader, mock_repos):
        resp = client_reader.get("/api/v1/author/1/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) == 3  # W1, W2, W3
        assert len(data["edges"]) == 2

    def test_graph_404(self, client_reader, mock_repos):
        mock_repos["author"].get_by_id.return_value = None
        resp = client_reader.get("/api/v1/author/999/graph")
        assert resp.status_code == 404

    def test_graph_empty_citations(self, client_reader, mock_repos):
        mock_repos["citation"].get_by_target_author.return_value = []
        resp = client_reader.get("/api/v1/author/1/graph")
        assert resp.status_code == 200
        assert resp.json()["nodes"] == []
        assert resp.json()["edges"] == []
