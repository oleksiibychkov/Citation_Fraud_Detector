"""Tests for batch analysis endpoint."""

from __future__ import annotations

import io
from unittest.mock import MagicMock

from cfd.api.dependencies import get_pipeline


class TestBatchAnalyze:
    def test_batch_success(self, app, client_analyst, mock_repos):
        mock_pipeline = MagicMock()
        result_mock = MagicMock()
        result_mock.status = "completed"
        result_mock.fraud_score = 0.35
        result_mock.confidence_level = "moderate"
        mock_pipeline.analyze.return_value = result_mock
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

        csv_content = b"surname,scopus_id,orcid\nIvanenko,57200000001,\nPetrenko,57200000002,\n"
        resp = client_analyst.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["processed"] == 2
        assert len(data["results"]) == 2

    def test_batch_empty_csv(self, app, client_analyst, mock_repos):
        mock_pipeline = MagicMock()
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

        csv_content = b"surname,scopus_id,orcid\n"
        resp = client_analyst.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_batch_analysis_error(self, app, client_analyst, mock_repos):
        mock_pipeline = MagicMock()
        mock_pipeline.analyze.side_effect = Exception("API error")
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

        csv_content = b"surname,scopus_id,orcid\nIvanenko,57200000001,\n"
        resp = client_analyst.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["status"] == "error"
        assert data["processed"] == 0

    def test_batch_reader_forbidden(self, app, client_reader, mock_repos):
        mock_pipeline = MagicMock()
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

        csv_content = b"surname,scopus_id,orcid\nIvanenko,57200000001,\n"
        resp = client_reader.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 403

    def test_batch_admin_allowed(self, app, client_admin, mock_repos):
        mock_pipeline = MagicMock()
        result_mock = MagicMock()
        result_mock.status = "completed"
        result_mock.fraud_score = 0.10
        result_mock.confidence_level = "normal"
        mock_pipeline.analyze.return_value = result_mock
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

        csv_content = b"surname,scopus_id,orcid\nIvanenko,57200000001,\n"
        resp = client_admin.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 200

    def test_batch_logs_audit(self, app, client_analyst, mock_repos):
        mock_pipeline = MagicMock()
        result_mock = MagicMock()
        result_mock.status = "completed"
        result_mock.fraud_score = 0.10
        result_mock.confidence_level = "normal"
        mock_pipeline.analyze.return_value = result_mock
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

        csv_content = b"surname,scopus_id,orcid\nIvanenko,57200000001,\n"
        client_analyst.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", io.BytesIO(csv_content), "text/csv")},
        )
        mock_repos["audit"].log.assert_called_once()
        call_args = mock_repos["audit"].log.call_args
        assert call_args[0][0] == "batch_analyze"
