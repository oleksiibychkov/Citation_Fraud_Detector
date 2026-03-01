"""Tests for JSON report export."""

import json

import pytest

from cfd.analysis.pipeline import AnalysisResult
from cfd.config.settings import Settings
from cfd.data.models import AuthorProfile
from cfd.export.json_export import export_to_json, result_to_dict
from cfd.graph.metrics import IndicatorResult


@pytest.fixture
def settings():
    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        scopus_api_key="test-key",
    )


@pytest.fixture
def analysis_result():
    return AnalysisResult(
        author_profile=AuthorProfile(
            scopus_id="57200000001",
            orcid="0000-0002-1234-5678",
            surname="Ivanenko",
            full_name="Oleksandr Ivanenko",
            institution="Kyiv National University",
            discipline="Computer Science",
            h_index=15,
            publication_count=50,
            citation_count=500,
            source_api="openalex",
        ),
        indicators=[
            IndicatorResult("SCR", 0.15, {"self_citations": 3, "total_citations": 20}),
            IndicatorResult("MCR", 0.05, {}),
            IndicatorResult("CB", 0.20, {}),
            IndicatorResult("TA", 0.10, {"max_z_score": 1.5}),
            IndicatorResult("HTA", 0.08, {"max_z_score": 1.0}),
        ],
        fraud_score=0.12,
        confidence_level="normal",
        triggered_indicators=[],
        status="completed",
        warnings=[],
    )


class TestExportToJson:
    def test_creates_file(self, analysis_result, settings, tmp_path):
        output = tmp_path / "report.json"
        export_to_json(analysis_result, output, settings)
        assert output.exists()

    def test_valid_json(self, analysis_result, settings, tmp_path):
        output = tmp_path / "report.json"
        export_to_json(analysis_result, output, settings)
        with open(output, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_required_fields(self, analysis_result, settings, tmp_path):
        output = tmp_path / "report.json"
        export_to_json(analysis_result, output, settings)
        with open(output, encoding="utf-8") as f:
            data = json.load(f)

        assert data["report_version"] == "1.0"
        assert data["algorithm_version"] == settings.algorithm_version
        assert "generated_at" in data
        assert "disclaimer" in data
        assert "author" in data
        assert "analysis" in data
        assert "indicators" in data
        assert "thresholds" in data

    def test_author_fields(self, analysis_result, settings, tmp_path):
        output = tmp_path / "report.json"
        export_to_json(analysis_result, output, settings)
        with open(output, encoding="utf-8") as f:
            data = json.load(f)

        author = data["author"]
        assert author["surname"] == "Ivanenko"
        assert author["full_name"] == "Oleksandr Ivanenko"
        assert author["scopus_id"] == "57200000001"
        assert author["orcid"] == "0000-0002-1234-5678"
        assert author["h_index"] == 15

    def test_analysis_fields(self, analysis_result, settings, tmp_path):
        output = tmp_path / "report.json"
        export_to_json(analysis_result, output, settings)
        with open(output, encoding="utf-8") as f:
            data = json.load(f)

        analysis = data["analysis"]
        assert analysis["status"] == "completed"
        assert analysis["fraud_score"] == 0.12
        assert analysis["confidence_level"] == "normal"
        assert isinstance(analysis["triggered_indicators"], list)

    def test_indicators_list(self, analysis_result, settings, tmp_path):
        output = tmp_path / "report.json"
        export_to_json(analysis_result, output, settings)
        with open(output, encoding="utf-8") as f:
            data = json.load(f)

        indicators = data["indicators"]
        assert len(indicators) == 5
        types = [ind["type"] for ind in indicators]
        assert "SCR" in types
        assert "MCR" in types

    def test_creates_parent_dirs(self, analysis_result, settings, tmp_path):
        output = tmp_path / "nested" / "dir" / "report.json"
        export_to_json(analysis_result, output, settings)
        assert output.exists()

    def test_without_settings(self, analysis_result, tmp_path):
        output = tmp_path / "report.json"
        export_to_json(analysis_result, output)
        assert output.exists()


class TestResultToDict:
    def test_basic_structure(self, analysis_result, settings):
        d = result_to_dict(analysis_result, settings)
        assert "author" in d
        assert "status" in d
        assert "fraud_score" in d
        assert "confidence_level" in d
        assert "indicators" in d
        assert "algorithm_version" in d

    def test_indicator_values(self, analysis_result, settings):
        d = result_to_dict(analysis_result, settings)
        assert d["indicators"]["SCR"] == pytest.approx(0.15)
        assert d["fraud_score"] == 0.12

    def test_author_info(self, analysis_result, settings):
        d = result_to_dict(analysis_result, settings)
        assert d["author"]["surname"] == "Ivanenko"
        assert d["author"]["full_name"] == "Oleksandr Ivanenko"
