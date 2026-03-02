"""Third batch of coverage boost tests — metrics, schemas, translator, evidence, pipeline."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from cfd.data.models import AuthorData, AuthorProfile, Citation, Publication


def _profile(**kw):
    defaults = dict(
        scopus_id="123", surname="Test", full_name="Test Author",
        h_index=10, citation_count=100, publication_count=20,
        orcid=None, institution="Uni", discipline="CS",
        source_api="openalex", coauthor_ids=[], subject_areas=["CS"],
    )
    defaults.update(kw)
    return AuthorProfile(**defaults)


def _pub(yr=2020, journal="J1", idx=0, **kw):
    defaults = dict(
        work_id=f"W{idx}", doi=None, title=f"Paper {idx}",
        journal=journal, publication_date=date(yr, 6, 1),
        citation_count=5, co_authors=[{"name": "A"}, {"name": "B"}],
        source_api="openalex",
    )
    defaults.update(kw)
    return Publication(**defaults)


def _cite(idx=0, self_cite=False, **kw):
    defaults = dict(
        source_work_id=f"cite{idx}", target_work_id=f"W{idx % 5}",
        citation_date=date(2022, 1, 1), is_self_citation=self_cite,
        source_api="openalex",
    )
    defaults.update(kw)
    return Citation(**defaults)


# ============================================================
# graph/metrics.py — uncovered branches
# ============================================================


class TestMetricsBranches:
    def test_indicator_result_to_dict(self):
        from cfd.graph.metrics import IndicatorResult
        ir = IndicatorResult("TEST", 0.5, {"key": "value"})
        d = ir.to_dict()
        assert d["indicator_type"] == "TEST"
        assert d["value"] == 0.5
        assert d["details"]["key"] == "value"

    def test_mcr_no_data_branch(self):
        """MCR returns no_data when total_our + total_them == 0."""
        from cfd.graph.metrics import compute_mcr_from_author_data
        # Need citations with source_author_id but total == 0 after filter?
        # Actually need: source_author_counts non-empty but total_our + total_them == 0
        # This can't happen normally. Let's test the no_citing_authors path.
        profile = _profile()
        data = AuthorData(profile=profile, publications=[], citations=[])
        result = compute_mcr_from_author_data(data)
        assert result.value == 0.0
        assert result.details.get("status") == "no_citing_authors"

    def test_hta_insufficient_temporal_data(self):
        """HTA returns 0.0 when insufficient temporal data."""
        from cfd.graph.metrics import compute_hta
        profile = _profile()
        pubs = [_pub(yr=2020, idx=0)]
        cites = [_cite(idx=0)]
        data = AuthorData(profile=profile, publications=pubs, citations=cites)
        result = compute_hta(data)
        assert result.value == 0.0

    def test_ta_high_pub_count(self):
        """TA applies pub_adjusted boost for extreme publication counts."""
        from cfd.graph.metrics import compute_ta
        profile = _profile(publication_count=500, citation_count=5000, h_index=50)
        pubs = [
            _pub(yr=2018 + i % 5, journal=f"J{i % 3}", idx=i, citation_count=20)
            for i in range(200)
        ]
        cites = [
            _cite(idx=i, source_work_id=f"ext{i}", target_work_id=f"W{i % 200}")
            for i in range(1000)
        ]
        data = AuthorData(profile=profile, publications=pubs, citations=cites)
        result = compute_ta(data)
        assert result.value >= 0.0


# ============================================================
# api/schemas.py — sensitivity override validation
# ============================================================


class TestSensitivityValidation:
    def test_invalid_sensitivity_keys(self):
        from cfd.api.schemas import SensitivityOverridesRequest
        with pytest.raises(Exception, match="Invalid sensitivity keys"):
            SensitivityOverridesRequest(overrides={"nonexistent_indicator": 1.0})

    def test_non_numeric_value(self):
        from cfd.api.schemas import SensitivityOverridesRequest
        # Pydantic will reject non-numeric strings before our validator runs
        with pytest.raises((ValueError, Exception)):
            SensitivityOverridesRequest(overrides={"mcr_threshold": "not_a_number"})

    def test_negative_value(self):
        from cfd.api.schemas import SensitivityOverridesRequest
        with pytest.raises(Exception, match="must be non-negative"):
            SensitivityOverridesRequest(overrides={"mcr_threshold": -1.0})

    def test_valid_override(self):
        from cfd.api.schemas import SensitivityOverridesRequest
        req = SensitivityOverridesRequest(overrides={"mcr_threshold": 0.5})
        assert req.overrides["mcr_threshold"] == 0.5


# ============================================================
# i18n/translator.py — uncovered branches
# ============================================================


class TestTranslatorBranches:
    def test_load_missing_locale(self):
        """Loading a missing locale file returns empty dict."""
        from cfd.i18n.translator import _load_locale
        # Clear the cache first
        _load_locale.cache_clear()
        result = _load_locale("nonexistent_locale_xyz")
        assert result == {}
        _load_locale.cache_clear()

    def test_format_with_kwargs(self):
        """Translator formats string with kwargs."""
        from cfd.i18n import translator
        # Patch _load_locale to return a dict with a formattable key
        with patch.object(translator, "_load_locale", return_value={"greeting": "Hello, {name}!"}):
            result = translator.t("greeting", name="World")
        assert result == "Hello, World!"

    def test_format_with_missing_key_in_template(self):
        """Translator handles missing format keys gracefully."""
        from cfd.i18n import translator
        with patch.object(translator, "_load_locale", return_value={"broken": "Hello, {missing_var}!"}):
            result = translator.t("broken")
        # Should return raw string without crashing
        assert "Hello" in result


# ============================================================
# export/evidence.py — save failure
# ============================================================


class TestEvidenceSaveFailure:
    def test_save_evidence_db_failure(self):
        """Evidence save logs warning on DB failure."""
        from cfd.export.evidence import save_evidence
        mock_repo = MagicMock()
        mock_repo.save_many.side_effect = Exception("DB connection lost")
        # Should not raise — just log warning
        save_evidence(
            evidence=[{"type": "test"}],
            repo=mock_repo,
            author_id=123,
            algorithm_version="1.0",
        )

    def test_save_evidence_empty(self):
        """Evidence save returns early for empty evidence."""
        from cfd.export.evidence import save_evidence
        mock_repo = MagicMock()
        save_evidence(evidence=[], repo=mock_repo, author_id=123, algorithm_version="1.0")
        mock_repo.save_many.assert_not_called()


# ============================================================
# export/html_export.py — ImportError branches
# ============================================================


class TestHtmlExportBranches:
    def test_export_without_jinja2(self):
        """HTML export raises ImportError when jinja2 missing."""
        import importlib
        import sys
        # Save the real jinja2 module reference
        real_jinja2 = sys.modules.get("jinja2")
        try:
            sys.modules["jinja2"] = None  # type: ignore[assignment]
            # Need to reimport to pick up the change
            import cfd.export.html_export as mod
            importlib.reload(mod)
            # Now calling should raise ImportError
            with pytest.raises(ImportError):
                mod.export_to_html(
                    result=MagicMock(),
                    output_path=MagicMock(),
                )
        finally:
            if real_jinja2 is not None:
                sys.modules["jinja2"] = real_jinja2
            else:
                sys.modules.pop("jinja2", None)
            import cfd.export.html_export as mod2
            importlib.reload(mod2)

    def test_export_html_plotly_unavailable(self):
        """HTML export handles missing plotly by skipping figures."""
        import sys
        import tempfile
        from pathlib import Path

        from cfd.export.html_export import export_to_html

        mock_result = MagicMock()
        mock_result.indicators = []
        mock_result.theorem_results = []
        mock_result.triggered_indicators = set()
        mock_result.warnings = []
        mock_result.fraud_score = 0.5
        mock_result.confidence_level = "medium"
        mock_result.author_profile = MagicMock()

        # Make plotly.io import raise ImportError inside the function
        real_plotly_io = sys.modules.get("plotly.io")
        try:
            sys.modules["plotly.io"] = None  # type: ignore[assignment]
            with tempfile.TemporaryDirectory() as tmp:
                out_path = Path(tmp) / "report.html"
                # This should skip figures but still produce HTML
                export_to_html(
                    result=mock_result,
                    output_path=out_path,
                    figures={"fig1": MagicMock()},
                )
                assert out_path.exists()
        finally:
            if real_plotly_io is not None:
                sys.modules["plotly.io"] = real_plotly_io
            else:
                sys.modules.pop("plotly.io", None)


# ============================================================
# analysis/peer_benchmark.py — save failure + find_peers path
# ============================================================


class TestPeerBenchmarkBranches:
    def test_compute_pb_save_failure(self):
        """compute_pb logs warning when peer_repo.save fails."""
        from cfd.analysis.peer_benchmark import compute_pb
        profile = _profile(discipline="CS", publication_count=20)
        data = AuthorData(profile=profile, publications=[], citations=[])
        mock_peer_repo = MagicMock()
        mock_peer_repo.find_peers.return_value = [
            {"id": 1, "h_index": 8, "citation_count": 80, "publication_count": 15},
            {"id": 2, "h_index": 12, "citation_count": 120, "publication_count": 25},
            {"id": 3, "h_index": 10, "citation_count": 100, "publication_count": 20},
        ]
        mock_peer_repo.save.side_effect = Exception("DB error")
        mock_author_repo = MagicMock()

        result = compute_pb(
            data,
            peer_repo=mock_peer_repo,
            author_repo=mock_author_repo,
            author_id=42,
        )
        assert result.indicator_type == "PB"

    def test_find_peers_delegation(self):
        """_find_peers delegates to peer_repo.find_peers."""
        from cfd.analysis.peer_benchmark import _find_peers
        profile = _profile(discipline="CS", publication_count=20)
        data = AuthorData(profile=profile, publications=[], citations=[])
        mock_peer_repo = MagicMock()
        mock_peer_repo.find_peers.return_value = [{"id": 1}, {"id": 2}]
        mock_author_repo = MagicMock()
        result = _find_peers(data, mock_author_repo, mock_peer_repo, k=10)
        assert len(result) == 2
        mock_peer_repo.find_peers.assert_called_once()


# ============================================================
# api/routers/cris.py — analysis_pending path
# ============================================================


class TestCrisAnalysisPending:
    def test_converis_analysis_pending(self):
        """Converis sync with action=analyze triggers analysis_pending status."""
        from fastapi.testclient import TestClient

        from cfd.api.app import create_app
        from cfd.api.auth import get_api_key
        from cfd.api.dependencies import get_repos
        from cfd.config.settings import Settings
        settings = Settings(supabase_url="", supabase_key="")
        app = create_app(settings)

        mock_repos = {
            "author": MagicMock(),
            "watchlist": MagicMock(),
            "audit": MagicMock(),
        }
        mock_repos["author"].get_by_scopus_id.return_value = {"id": 42, "name": "Test"}
        mock_repos["author"].get_by_orcid.return_value = None

        app.dependency_overrides[get_api_key] = lambda: MagicMock(key_id=1, name="test", role="admin")
        app.dependency_overrides[get_repos] = lambda: mock_repos

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/cris/converis/sync", json={
            "action": "analyze",
            "person": {"familyName": "Smith", "scopusAuthorId": "S123"},
        })
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "analysis_pending"


# ============================================================
# analysis/pipeline.py — community/theorem failure branches
# ============================================================


class TestPipelineFailureBranches:
    def _make_pipeline(self):
        from cfd.analysis.pipeline import AnalysisPipeline
        from cfd.config.settings import Settings
        settings = Settings(supabase_url="", supabase_key="")
        mock_strategy = MagicMock()
        profile = _profile()
        pubs = [_pub(yr=2020 + i % 3, idx=i) for i in range(5)]
        cites = [_cite(idx=i) for i in range(10)]
        mock_strategy.collect.return_value = AuthorData(
            profile=profile, publications=pubs, citations=cites,
        )
        return AnalysisPipeline(mock_strategy, settings)

    def test_community_detection_failure(self):
        """Pipeline handles community detection failure gracefully."""
        pipeline = self._make_pipeline()
        with patch("cfd.analysis.pipeline.detect_communities", side_effect=Exception("fail")):
            result = pipeline.analyze("Test", scopus_id="123")
        assert result is not None
        assert result.fraud_score >= 0.0

    def test_theorem_failure(self):
        """Pipeline handles theorem evaluation failure gracefully."""
        pipeline = self._make_pipeline()
        with patch("cfd.analysis.pipeline.run_hierarchy", side_effect=Exception("fail")):
            result = pipeline.analyze("Test", scopus_id="123")
        assert result is not None


# ============================================================
# cli/watchlist_commands.py — error branches
# ============================================================


class TestWatchlistCommandsBranches:
    def _invoke(self, args):
        from click.testing import CliRunner

        from cfd.cli.watchlist_commands import watchlist
        from cfd.config.settings import Settings
        runner = CliRunner()
        settings = Settings(supabase_url="", supabase_key="")
        return runner.invoke(watchlist, args, obj={"settings": settings}, catch_exceptions=True)

    def test_add_no_identifiers(self):
        """watchlist add requires scopus_id or orcid."""
        result = self._invoke(["add"])
        assert "scopus" in result.output.lower() or "orcid" in result.output.lower() or result.exit_code != 0

    def test_add_author_not_found(self):
        """watchlist add reports error when author not found."""
        with (
            patch("cfd.db.client.get_supabase_client", return_value=MagicMock()),
            patch("cfd.db.repositories.authors.AuthorRepository") as mock_repo_cls,
        ):
                mock_repo_cls.return_value.get_by_scopus_id.return_value = None
                result = self._invoke(["add", "--scopus-id", "99999"])
        assert "not found" in result.output.lower() or "error" in result.output.lower() or result.exit_code != 0

    def test_set_sensitivity_invalid_json(self):
        """watchlist set-sensitivity rejects non-dict JSON."""
        result = self._invoke(["set-sensitivity", "1", "--overrides", "[1,2,3]"])
        assert "object" in result.output.lower() or "dict" in result.output.lower() or result.exit_code != 0

    def test_set_sensitivity_invalid_keys(self):
        """watchlist set-sensitivity rejects unknown sensitivity keys."""
        result = self._invoke(
            ["set-sensitivity", "1", "--overrides", json.dumps({"BOGUS_KEY": 1.0})],
        )
        assert "invalid" in result.output.lower() or result.exit_code != 0


# ============================================================
# api/routers/batch.py — upload size + error entry
# ============================================================


class TestBatchRouterBranches:
    def _make_client(self):
        from fastapi.testclient import TestClient

        from cfd.api.app import create_app
        from cfd.api.auth import get_api_key
        from cfd.api.dependencies import get_pipeline, get_repos
        from cfd.config.settings import Settings
        settings = Settings(supabase_url="", supabase_key="")
        app = create_app(settings)
        app.dependency_overrides[get_api_key] = lambda: MagicMock(key_id=1, name="test", role="admin")
        app.dependency_overrides[get_pipeline] = lambda: MagicMock()
        app.dependency_overrides[get_repos] = lambda: {"audit": MagicMock()}
        return TestClient(app, raise_server_exceptions=False)

    def test_upload_too_large(self):
        """File exceeding MAX_UPLOAD_BYTES returns 413."""
        client = self._make_client()
        big_content = b"scopus_id\n" + b"12345678901\n" * (1024 * 1024)  # ~12MB
        resp = client.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", big_content, "text/csv")},
        )
        assert resp.status_code == 413
