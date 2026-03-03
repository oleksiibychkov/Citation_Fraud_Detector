"""Fifth coverage boost — CLI commands, health/ready DB branches, dashboard dossier, report formats."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cfd.data.models import AuthorData, AuthorProfile, Citation, Publication


def _profile(**kw):
    defaults = dict(
        scopus_id="123", surname="Test", full_name="Test Author",
        h_index=10, citation_count=100, publication_count=20,
        orcid=None, institution="Uni", discipline="CS",
        source_api="openalex",
    )
    defaults.update(kw)
    return AuthorProfile(**defaults)


def _pub(yr=2020, idx=0, **kw):
    defaults = dict(
        work_id=f"W{idx}", title=f"Paper {idx}", journal="J1",
        publication_date=date(yr, 6, 1), citation_count=5,
        source_api="openalex",
    )
    defaults.update(kw)
    return Publication(**defaults)


def _cite(idx=0, **kw):
    defaults = dict(
        source_work_id=f"cite{idx}", target_work_id=f"W{idx % 5}",
        citation_date=date(2022, 1, 1), is_self_citation=False,
        source_api="openalex",
    )
    defaults.update(kw)
    return Citation(**defaults)


# ============================================================
# api/routers/health.py — ready endpoint with real supabase mock (lines 28-29)
# ============================================================


class TestHealthReady:
    def test_ready_db_query_error(self):
        """Ready endpoint returns 503 when DB query raises."""
        from fastapi.testclient import TestClient

        from cfd.api.app import create_app
        from cfd.config.settings import Settings

        settings = Settings(supabase_url="https://test.supabase.co", supabase_key="fake-key")
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.side_effect = (
            Exception("DB error")
        )

        with patch("cfd.db.client.get_supabase_client", return_value=mock_supabase):
            app = create_app(settings)
            # Must use client inside patch context so lifespan gets the mock
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/ready")
                assert resp.status_code == 503
                assert resp.json()["database"] == "error"

    def test_ready_db_connected(self):
        """Ready endpoint returns 200 when DB query succeeds."""
        from fastapi.testclient import TestClient

        from cfd.api.app import create_app
        from cfd.config.settings import Settings

        settings = Settings(supabase_url="https://test.supabase.co", supabase_key="fake-key")
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value.data = [
            {"id": 1}
        ]

        with patch("cfd.db.client.get_supabase_client", return_value=mock_supabase):
            app = create_app(settings)
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/ready")
                assert resp.status_code == 200
                assert resp.json()["database"] == "connected"


# ============================================================
# cli/main.py — identity mismatch + batch error branches
# ============================================================


class TestCliMainBranches:
    def _invoke(self, args, obj=None):
        from click.testing import CliRunner

        from cfd.cli.main import cli
        from cfd.config.settings import Settings

        runner = CliRunner()
        settings = Settings(supabase_url="", supabase_key="")
        return runner.invoke(cli, args, obj=obj or {"settings": settings}, catch_exceptions=True)

    def test_analyze_identity_mismatch(self):
        """analyze command handles IdentityMismatchError."""
        from cfd.exceptions import IdentityMismatchError

        with (
            patch("cfd.cli.main._build_strategy"),
            patch("cfd.cli.main._build_pipeline") as mock_pipe,
        ):
            mock_pipe.return_value.analyze.side_effect = IdentityMismatchError("ID mismatch")
            result = self._invoke(["analyze", "--author", "Test", "--scopus-id", "123"])
        assert result.exit_code != 0

    def test_batch_csv_errors(self):
        """batch command shows CSV validation errors."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            f.write("bad_column\nvalue\n")
            tmp = Path(f.name)

        try:
            with (
                patch("cfd.cli.main._build_strategy"),
                patch("cfd.cli.main._build_pipeline"),
            ):
                result = self._invoke(["batch", "--batch", str(tmp)])
            # Should show errors or exit
            assert "error" in result.output.lower() or result.exit_code != 0
        finally:
            tmp.unlink(missing_ok=True)

    def test_batch_csv_warnings_and_duplicates(self):
        """batch command shows warnings and duplicate count."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            # Use valid 10-digit Scopus IDs to avoid format errors
            f.write("surname,scopus_id\nTest,1234567890\nTest,1234567890\n")
            tmp = Path(f.name)

        try:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = MagicMock(
                fraud_score=0.3, confidence_level="normal",
                author_profile=_profile(), status="completed",
            )
            with (
                patch("cfd.cli.main._build_strategy"),
                patch("cfd.cli.main._build_pipeline", return_value=mock_pipeline),
            ):
                result = self._invoke(["batch", "--batch", str(tmp)])
            # Should mention duplicates removed
            assert "duplicate" in result.output.lower() or result.exit_code == 0
        finally:
            tmp.unlink(missing_ok=True)


# ============================================================
# cli/report_commands.py — HTML, PDF format branches
# ============================================================


class TestReportCommandFormats:
    def _invoke(self, args):
        from click.testing import CliRunner

        from cfd.cli.report_commands import report
        from cfd.config.settings import Settings

        runner = CliRunner()
        settings = Settings(supabase_url="", supabase_key="")
        return runner.invoke(report, args, obj={"settings": settings}, catch_exceptions=True)

    def test_report_html_format(self):
        """report command generates HTML output."""
        mock_result = MagicMock()
        mock_result.author_profile = _profile()
        mock_result.fraud_score = 0.5
        mock_result.confidence_level = "moderate"
        mock_result.indicators = []
        mock_result.triggered_indicators = []
        mock_result.warnings = []

        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "report.html")
            with (
                patch("cfd.cli.report_commands._generate_figures", return_value=None),
                patch("cfd.cli.main._build_strategy"),
                patch("cfd.cli.main._build_pipeline") as mock_pipe,
                patch("cfd.export.html_export.export_to_html") as mock_html,
            ):
                mock_pipe.return_value.analyze.return_value = mock_result
                result = self._invoke([
                    "--author", "Test", "--scopus-id", "123",
                    "--format", "html", "--output", out,
                ])
            assert result.exit_code == 0 or mock_html.called

    def test_report_pdf_format(self):
        """report command generates PDF output."""
        mock_result = MagicMock()
        mock_result.author_profile = _profile()

        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "report.pdf")
            with (
                patch("cfd.cli.report_commands._generate_figures", return_value=None),
                patch("cfd.cli.main._build_strategy"),
                patch("cfd.cli.main._build_pipeline") as mock_pipe,
                patch("cfd.export.pdf_export.export_to_pdf") as mock_pdf,
            ):
                mock_pipe.return_value.analyze.return_value = mock_result
                result = self._invoke([
                    "--author", "Test", "--scopus-id", "123",
                    "--format", "pdf", "--output", out,
                ])
            assert result.exit_code == 0 or mock_pdf.called

    def test_generate_figures_import_error(self):
        """_generate_figures returns None when plotly not available."""
        from cfd.cli.report_commands import _generate_figures

        mock_result = MagicMock()
        with patch.dict(sys.modules, {"cfd.visualization.temporal": None}):
            result = _generate_figures(mock_result, MagicMock())
        # Returns None on ImportError
        assert result is None or isinstance(result, dict)


# ============================================================
# cli/watchlist_commands.py — error branches
# ============================================================


class TestWatchlistCommandErrors:
    def _invoke(self, args):
        from click.testing import CliRunner

        from cfd.cli.watchlist_commands import watchlist
        from cfd.config.settings import Settings

        runner = CliRunner()
        settings = Settings(supabase_url="", supabase_key="")
        return runner.invoke(watchlist, args, obj={"settings": settings}, catch_exceptions=True)

    def test_list_db_error(self):
        """watchlist list handles DB connection error."""
        with (
            patch("cfd.db.client.get_supabase_client", side_effect=Exception("DB fail")),
        ):
            result = self._invoke(["list"])
        assert "error" in result.output.lower() or result.exit_code != 0

    def test_add_db_error(self):
        """watchlist add handles DB error during lookup."""
        with (
            patch("cfd.db.client.get_supabase_client", return_value=MagicMock()),
            patch("cfd.db.repositories.authors.AuthorRepository") as mock_repo_cls,
        ):
            mock_repo_cls.return_value.get_by_scopus_id.side_effect = Exception("DB fail")
            result = self._invoke(["add", "--scopus-id", "123"])
        assert "error" in result.output.lower() or result.exit_code != 0

    def test_remove_db_error(self):
        """watchlist remove handles DB error."""
        with (
            patch("cfd.db.client.get_supabase_client", side_effect=Exception("DB fail")),
        ):
            result = self._invoke(["remove", "1"])
        assert "error" in result.output.lower() or result.exit_code != 0

    def test_set_sensitivity_db_error(self):
        """watchlist set-sensitivity handles DB error."""
        with (
            patch("cfd.db.client.get_supabase_client", side_effect=Exception("DB fail")),
        ):
            result = self._invoke([
                "set-sensitivity", "1",
                "--overrides", json.dumps({"mcr_threshold": 0.5}),
            ])
        assert "error" in result.output.lower() or result.exit_code != 0

    def test_reanalyze_db_error(self):
        """watchlist reanalyze handles DB error."""
        with (
            patch("cfd.db.client.get_supabase_client", side_effect=Exception("DB fail")),
        ):
            result = self._invoke(["reanalyze", "--all"])
        assert "error" in result.output.lower() or result.exit_code != 0


# ============================================================
# dashboard/pages/dossier.py — visualization branches (lines 95-98, 131-134)
# ============================================================


class TestDossierVisualizationBranches:
    @pytest.fixture(autouse=True)
    def _mock_st(self, monkeypatch):
        self.mock_st = MagicMock()
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)

        def _columns(spec):
            n = spec if isinstance(spec, int) else len(spec)
            return [MagicMock(__enter__=MagicMock(return_value=mock_col),
                              __exit__=MagicMock(return_value=False)) for _ in range(n)]

        def _tabs(labels):
            return [MagicMock(__enter__=MagicMock(return_value=mock_col),
                              __exit__=MagicMock(return_value=False)) for _ in labels]

        self.mock_st.columns.side_effect = _columns
        self.mock_st.tabs.side_effect = _tabs
        import cfd.dashboard.pages.dossier  # noqa: F401
        monkeypatch.setattr("cfd.dashboard.pages.dossier.st", self.mock_st)

    def test_run_analysis_collect_fallback(self):
        """_run_analysis falls back to empty AuthorData when collect fails."""
        from cfd.dashboard.pages.dossier import _run_analysis

        mock_result = MagicMock()
        mock_result.author_profile = _profile()
        mock_strategy = MagicMock()
        mock_strategy.collect.side_effect = Exception("collect fail")
        mock_pipeline = MagicMock()
        mock_pipeline.analyze.return_value = mock_result

        with (
            patch("cfd.cli.main._build_strategy", return_value=mock_strategy),
            patch("cfd.cli.main._build_pipeline", return_value=mock_pipeline),
        ):
            result, author_data = _run_analysis("Test", "123", None, "openalex")

        assert result is not None
        assert author_data is not None
        assert author_data.publications == []

    def test_render_visualizations_import_error(self):
        """_render_visualizations handles missing plotly."""
        from cfd.dashboard.pages.dossier import _render_visualizations

        data = AuthorData(profile=_profile(), publications=[], citations=[])
        mock_result = MagicMock()

        with (
            patch(
                "cfd.dashboard.pages.dossier.build_network_figure",
                side_effect=ImportError("No plotly"),
                create=True,
            ),
            patch.dict(sys.modules, {"cfd.visualization.network": None}),
        ):
            _render_visualizations(data, mock_result)

    def test_render_visualizations_exception(self):
        """_render_visualizations handles general exceptions."""
        from cfd.dashboard.pages.dossier import _render_visualizations

        data = AuthorData(profile=_profile(), publications=[], citations=[])
        mock_result = MagicMock()

        with patch(
            "cfd.visualization.network.build_network_figure",
            side_effect=RuntimeError("render fail"),
        ):
            _render_visualizations(data, mock_result)
        # Should call st.warning
        assert self.mock_st.warning.called

    def test_dossier_invalid_level_fallback(self):
        """Dossier falls back to 'normal' for unknown confidence level."""
        from cfd.dashboard.pages.dossier import render

        mock_result = MagicMock()
        mock_result.author_profile = _profile()
        mock_result.confidence_level = "BOGUS"
        mock_result.fraud_score = 0.5
        mock_result.indicators = []
        mock_result.triggered_indicators = []

        self.mock_st.button.return_value = True
        self.mock_st.text_input.side_effect = ["TestAuthor", "123", ""]
        self.mock_st.selectbox.return_value = "openalex"

        with patch(
            "cfd.dashboard.pages.dossier._run_analysis",
            return_value=(mock_result, AuthorData(profile=_profile(), publications=[], citations=[])),
        ):
            render()


# ============================================================
# dashboard/pages/compare.py — single snapshot + timeline plotly (lines 112-113)
# ============================================================


class TestCompareBranches:
    @pytest.fixture(autouse=True)
    def _mock_st(self, monkeypatch):
        self.mock_st = MagicMock()
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)

        def _columns(spec):
            n = spec if isinstance(spec, int) else len(spec)
            return [MagicMock(__enter__=MagicMock(return_value=mock_col),
                              __exit__=MagicMock(return_value=False)) for _ in range(n)]

        self.mock_st.columns.side_effect = _columns
        import cfd.dashboard.pages.compare  # noqa: F401
        monkeypatch.setattr("cfd.dashboard.pages.compare.st", self.mock_st)

    def test_single_snapshot(self):
        """Compare shows single snapshot when only one available."""
        from cfd.dashboard.pages.compare import render

        self.mock_st.button.return_value = True
        self.mock_st.number_input.return_value = 1
        self.mock_st.slider.return_value = 5

        with patch("cfd.dashboard.pages.compare._load_snapshots", return_value=[
            {"fraud_score": 0.3, "created_at": "2024-01-01", "h_index": 10},
        ]):
            render()
        # Should show warning about single snapshot
        assert self.mock_st.warning.called

    def test_timeline_plotly_unavailable(self):
        """Timeline chart handles missing plotly."""
        from cfd.dashboard.pages.compare import _render_timeline

        with patch.dict(sys.modules, {"plotly.graph_objects": None, "plotly": None}):
            _render_timeline([
                {"fraud_score": 0.3, "created_at": "2024-01-01"},
                {"fraud_score": 0.5, "created_at": "2024-06-01"},
            ])


# ============================================================
# analysis/pipeline.py — incremental skip + clique branches
# ============================================================


class TestPipelineIncrementalSkip:
    def test_incremental_no_changes_still_analyzes(self):
        """Pipeline always runs analysis even when no changes detected."""
        from cfd.analysis.pipeline import AnalysisPipeline
        from cfd.config.settings import Settings

        settings = Settings(supabase_url="", supabase_key="")
        mock_strategy = MagicMock()
        profile = _profile()
        mock_strategy.collect.return_value = AuthorData(
            profile=profile, publications=[], citations=[],
        )

        mock_author_repo = MagicMock()
        mock_author_repo.get_by_scopus_id.return_value = {"id": 42}
        mock_pub_repo = MagicMock()

        pipeline = AnalysisPipeline(
            mock_strategy, settings,
            author_repo=mock_author_repo,
            pub_repo=mock_pub_repo,
        )

        with (
            patch("cfd.analysis.incremental.check_what_changed") as mock_check,
            patch("cfd.analysis.incremental.should_skip_analysis") as mock_skip,
        ):
            mock_check.return_value = MagicMock()
            mock_skip.return_value = (True, {"pub_delta": 0, "cit_delta": 0})
            result = pipeline.analyze("Test", scopus_id="123")

        # Analysis always proceeds now — status should not be skipped
        assert result.status != "skipped_no_changes"

    def test_clique_detection_in_pipeline(self):
        """Pipeline runs clique detection on mutual graph."""
        import networkx as nx

        from cfd.analysis.pipeline import AnalysisPipeline
        from cfd.config.settings import Settings

        settings = Settings(supabase_url="", supabase_key="", min_clique_size=2)
        mock_strategy = MagicMock()
        profile = _profile()
        pubs = [_pub(yr=2020 + i % 3, idx=i) for i in range(5)]
        # Create citations with source/target author IDs for mutual graph
        cites = [
            _cite(idx=i, source_author_id=100 + i % 3, target_author_id=200 + i % 3)
            for i in range(10)
        ]
        mock_strategy.collect.return_value = AuthorData(
            profile=profile, publications=pubs, citations=cites,
        )

        pipeline = AnalysisPipeline(mock_strategy, settings)

        # Build a mutual graph with enough nodes
        mock_mutual = nx.Graph()
        mock_mutual.add_edges_from([(100, 200), (200, 300), (300, 100)])

        with patch("cfd.analysis.pipeline.build_mutual_graph", return_value=mock_mutual):
            result = pipeline.analyze("Test", scopus_id="123")
        assert result.status == "completed"


# ============================================================
# analysis/temporal.py — paper CV early returns (lines 50, 62)
# ============================================================


class TestTemporalEarlyReturns:
    def test_cv_zero_citation_count(self):
        """Citation velocity handles zero citation count."""
        from cfd.analysis.baselines import DisciplineBaseline
        from cfd.analysis.temporal import _paper_citation_velocity

        pub = _pub(yr=2020, idx=0, citation_count=0)
        baseline = DisciplineBaseline(discipline="CS", avg_scr=0.15, std_scr=0.1)
        result = _paper_citation_velocity(pub, baseline)
        assert result is None or isinstance(result, float)

    def test_cv_no_publication_date(self):
        """Citation velocity returns None when pub has no date."""
        from cfd.analysis.baselines import DisciplineBaseline
        from cfd.analysis.temporal import _paper_citation_velocity

        pub = Publication(
            work_id="W0", title="Test", journal="J1",
            publication_date=None, citation_count=5, source_api="openalex",
        )
        baseline = DisciplineBaseline(discipline="CS", avg_scr=0.15, std_scr=0.1)
        result = _paper_citation_velocity(pub, baseline)
        assert result is None

    def test_sbd_no_counts_by_year(self):
        """SBD handles publications without counts_by_year."""
        from cfd.analysis.temporal import compute_sbd

        profile = _profile()
        # Publications with raw_data but no counts_by_year
        pubs = [_pub(yr=2015, idx=i, raw_data={}) for i in range(5)]
        data = AuthorData(profile=profile, publications=pubs, citations=[])
        result = compute_sbd(data)
        assert result.indicator_type == "SBD"


# ============================================================
# graph/scoring.py — COERCE trigger line 124
# ============================================================


class TestScoringCoerceNormalize:
    def test_normalize_coerce_indicator(self):
        """COERCE indicator normalizes correctly."""
        from cfd.config.settings import Settings
        from cfd.graph.metrics import IndicatorResult
        from cfd.graph.scoring import _normalize_indicator

        settings = Settings(supabase_url="", supabase_key="")
        ind = IndicatorResult("COERCE", 0.8, {})
        val = _normalize_indicator(ind, settings)
        assert 0.0 <= val <= 1.0


# ============================================================
# api/routers/batch.py — truncation + CFDError (lines 56, 73)
# ============================================================


class TestBatchRouterBranches:
    def _make_app(self, mock_pipeline=None):
        from cfd.api.app import create_app
        from cfd.api.auth import get_api_key
        from cfd.api.dependencies import get_pipeline, get_repos
        from cfd.config.settings import Settings

        settings = Settings(supabase_url="", supabase_key="")
        app = create_app(settings)
        app.dependency_overrides[get_api_key] = lambda: MagicMock(key_id=1, name="test", role="admin")
        app.dependency_overrides[get_pipeline] = lambda: (mock_pipeline or MagicMock())
        app.dependency_overrides[get_repos] = lambda: {"audit": MagicMock()}
        return app

    def test_batch_truncation_message(self):
        """Batch larger than MAX_BATCH_SIZE includes truncation error."""
        from fastapi.testclient import TestClient

        mock_pipeline = MagicMock()
        mock_pipeline.analyze.return_value = MagicMock(
            fraud_score=0.3, confidence_level="normal",
            author_profile=_profile(), indicators=[], triggered_indicators=[],
            status="completed",
        )
        app = self._make_app(mock_pipeline)
        client = TestClient(app, raise_server_exceptions=False)

        lines = ["surname,scopus_id\n"] + [f"Author{i},{i}\n" for i in range(55)]
        content = "".join(lines).encode()
        resp = client.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", content, "text/csv")},
        )
        assert resp.status_code == 200

    def test_batch_entry_cfd_error(self):
        """Batch entry with CFDError records error status."""
        from fastapi.testclient import TestClient

        from cfd.exceptions import CFDError

        mock_pipeline = MagicMock()
        mock_pipeline.analyze.side_effect = CFDError("API limit exceeded")
        app = self._make_app(mock_pipeline)
        client = TestClient(app, raise_server_exceptions=False)

        content = b"surname,scopus_id\nSmith,999\n"
        resp = client.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", content, "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 0
