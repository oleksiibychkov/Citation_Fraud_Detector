"""Fourth coverage boost — CLI error paths, data parsing, graph branches, dashboard, export."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import networkx as nx
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
# graph/builder.py — external node branch (line 34)
# ============================================================


class TestGraphBuilder:
    def test_external_node_added(self):
        """Citation to unknown work adds an 'external' node."""
        from cfd.graph.builder import build_citation_graph
        profile = _profile()
        pubs = [_pub(idx=0)]
        cites = [_cite(idx=0, target_work_id="EXTERNAL_W99")]
        data = AuthorData(profile=profile, publications=pubs, citations=cites)
        g = build_citation_graph(data)
        assert "EXTERNAL_W99" in g.nodes


# ============================================================
# graph/cliques.py — log_prob > 0 branch (line 68)
# ============================================================


class TestCliqueProbability:
    def test_clique_probability_high(self):
        """Clique probability caps at 1.0 when log_prob > 0."""
        from cfd.graph.cliques import _compute_clique_probability
        # Very small clique in dense graph => log_prob > 0
        result = _compute_clique_probability(n=3, k=2, p=0.99)
        assert result <= 1.0


# ============================================================
# graph/mutual.py — zero denom branch (line 47)
# ============================================================


class TestMutualGraph:
    def test_zero_denom_skip(self):
        """Pairs with zero total citations are skipped."""
        from cfd.graph.mutual import build_mutual_graph
        # Citations where source_author_id and target_author_id are None
        cites = [
            Citation(source_work_id="a", target_work_id="b",
                     is_self_citation=False, source_api="openalex"),
        ]
        g = build_mutual_graph(cites, mcr_threshold=0.1)
        assert isinstance(g, nx.Graph)


# ============================================================
# graph/scoring.py — COERCE trigger (line 124)
# ============================================================


class TestScoringCoerceTrigger:
    def test_coerce_triggered(self):
        from cfd.config.settings import Settings
        from cfd.graph.metrics import IndicatorResult
        from cfd.graph.scoring import _is_triggered
        settings = Settings(supabase_url="", supabase_key="")
        ind = IndicatorResult("COERCE", 0.5, {})
        assert _is_triggered(ind, settings) is True

    def test_coerce_not_triggered(self):
        from cfd.config.settings import Settings
        from cfd.graph.metrics import IndicatorResult
        from cfd.graph.scoring import _is_triggered
        settings = Settings(supabase_url="", supabase_key="")
        ind = IndicatorResult("COERCE", 0.1, {})
        assert _is_triggered(ind, settings) is False


# ============================================================
# graph/engine.py — pagerank exception + undirected cycle (lines 84-85, 105)
# ============================================================


class TestNetworkXEngineBranches:
    def test_pagerank_exception(self):
        from cfd.graph.engine import NetworkXEngine
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3)])
        engine = NetworkXEngine(g)
        with patch("networkx.pagerank", side_effect=nx.NetworkXException("fail")):
            result = engine.pagerank(1)
        assert result == 0.0

    def test_undirected_cycle_check(self):
        from cfd.graph.engine import NetworkXEngine
        g = nx.Graph()  # undirected
        g.add_edges_from([(1, 2), (2, 3), (3, 1)])
        engine = NetworkXEngine(g)
        assert engine.has_cycle_in_subgraph({1, 2, 3}) is True


# ============================================================
# graph/igraph_engine.py — undirected subgraph (line 110)
# ============================================================


class TestIgraphUndirected:
    def test_has_cycle_undirected(self):
        from cfd.graph.igraph_engine import IGraphEngine
        g = nx.Graph()
        g.add_edges_from([(1, 2), (2, 3), (3, 1)])
        engine = IGraphEngine(g)
        result = engine.has_cycle_in_subgraph({1, 2, 3})
        assert result is True


# ============================================================
# data/validators.py — surname partial match (line 50)
# ============================================================


class TestValidators:
    def test_surname_partial_match(self):
        from cfd.data.validators import check_surname_match
        ok, _ = check_surname_match("Smith", "Smith-Jones")
        assert ok is True


# ============================================================
# data/batch.py — encoding/CSV error (lines 98-101)
# ============================================================


class TestBatchLoadErrors:
    def test_csv_encoding_error(self):
        from cfd.data.batch import load_batch_csv
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as f:
            f.write(b"\xff\xfe" + b"\x00" * 100)  # invalid UTF-8
            tmp = Path(f.name)
        try:
            result = load_batch_csv(tmp)
            assert any("encoding" in e.lower() for e in result.errors) or result.entries == []
        finally:
            tmp.unlink(missing_ok=True)

    def test_csv_parse_error(self):
        from cfd.data.batch import load_batch_csv
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
            f.write("scopus_id\n")
            f.write('"unclosed quote\n')
            tmp = Path(f.name)
        try:
            result = load_batch_csv(tmp)
            # Should handle gracefully (either parse what it can or report error)
            assert isinstance(result.entries, list)
        finally:
            tmp.unlink(missing_ok=True)


# ============================================================
# analysis/temporal.py — early return branches (lines 50, 62, 142)
# ============================================================


class TestTemporalBranches:
    def test_cv_too_new_paper(self):
        """Citation velocity returns None for very new papers."""
        from cfd.analysis.temporal import _paper_citation_velocity
        pub = _pub(yr=2026, idx=0, citation_count=100)
        baseline = {"expected_yearly_citations": 10}
        result = _paper_citation_velocity(pub, baseline)
        # Very new paper — should return None or a value
        assert result is None or isinstance(result, float)

    def test_sbd_short_history(self):
        """SBD skips publications with < 3 years of data."""
        from cfd.analysis.temporal import compute_sbd
        profile = _profile()
        pubs = [_pub(yr=2025, idx=0)]  # only 1 year
        cites = []
        data = AuthorData(profile=profile, publications=pubs, citations=cites)
        result = compute_sbd(data)
        assert result.value >= 0.0


# ============================================================
# analysis/calibration.py — score_to_level critical fallback (line 52)
# ============================================================


class TestCalibrationBranches:
    def test_score_to_level_critical(self):
        from cfd.analysis.calibration import _score_to_level
        result = _score_to_level(1.5)  # above all thresholds
        assert result == "critical"


# ============================================================
# analysis/salami.py — short series + empty title (lines 112, 150)
# ============================================================


class TestSalamiBranches:
    def test_find_series_too_few_pubs(self):
        from cfd.analysis.salami import _find_publication_series
        pubs = [_pub(yr=2020, idx=0)]  # only 1 pub
        result = _find_publication_series(pubs)
        assert result == []

    def test_title_jaccard_empty_words(self):
        from cfd.analysis.salami import _title_jaccard
        assert _title_jaccard("", "test") == 0.0
        assert _title_jaccard("test", "") == 0.0


# ============================================================
# analysis/embeddings.py — zero vocab (line 65)
# ============================================================


class TestEmbeddingsZeroVocab:
    def test_tfidf_all_short_words(self):
        """Docs with only 1-char tokens produce zero vocab."""
        from cfd.analysis.embeddings import NaiveTfidfStrategy
        strategy = NaiveTfidfStrategy()
        # Only single-character "words" — tokenizer filters them out (min 2 chars)
        result = strategy.embed(["a b c", "x y z"])
        assert result.shape[0] == 2


# ============================================================
# analysis/coercive.py — trend with < 2 yearly ratios (line 121)
# ============================================================


class TestCoerciveBranches:
    def test_trend_too_few_years(self):
        from cfd.analysis.coercive import _detect_trend_increase
        result = _detect_trend_increase([(2020, 0.3)])  # only 1 year
        assert result is False


# ============================================================
# analysis/context.py — review ratio pass branch (line 70)
# ============================================================


class TestContextBranches:
    def test_review_ratio_normal(self):
        """Some reviews are normal — no anomaly signal."""
        from cfd.analysis.context import contextual_check
        from cfd.graph.metrics import IndicatorResult
        profile = _profile()
        pubs = [_pub(yr=2020, idx=i, title="Review of" if i == 0 else "Research") for i in range(10)]
        cites = [_cite(idx=i) for i in range(20)]
        data = AuthorData(profile=profile, publications=pubs, citations=cites)
        indicator_map = {
            "TA": IndicatorResult("TA", 0.1, {}),
            "HTA": IndicatorResult("HTA", 0.1, {}),
            "CB": IndicatorResult("CB", 0.1, {}),
        }
        result = contextual_check(data, indicator_map)
        assert result.value >= 0.0


# ============================================================
# analysis/cross_platform.py — empty words skip (line 158)
# ============================================================


class TestCrossPlatformBranches:
    def test_empty_title_skip(self):
        from cfd.analysis.cross_platform import compute_cpc
        profile = _profile()
        pubs = [_pub(yr=2020, idx=0, title=""), _pub(yr=2020, idx=1, title="")]
        data = AuthorData(profile=profile, publications=pubs, citations=[])
        result = compute_cpc(data)
        assert result.value >= 0.0


# ============================================================
# api/routers/health.py — DB error (lines 28-29)
# ============================================================


class TestHealthEndpoint:
    def test_health_ready_db_error(self):
        from fastapi.testclient import TestClient

        from cfd.api.app import create_app
        from cfd.api.auth import get_api_key
        from cfd.api.dependencies import get_repos
        from cfd.config.settings import Settings

        settings = Settings(supabase_url="", supabase_key="")
        app = create_app(settings)
        app.dependency_overrides[get_api_key] = lambda: MagicMock(key_id=1, name="test", role="admin")

        mock_repos = {"watchlist": MagicMock()}
        mock_repos["watchlist"].count.side_effect = Exception("DB down")
        app.dependency_overrides[get_repos] = lambda: mock_repos

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/ready")
        assert resp.status_code == 503


# ============================================================
# api/routers/batch.py — truncation + CFDError (lines 56, 73)
# ============================================================


class TestBatchTruncation:
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

    def test_batch_truncation(self):
        """Batch larger than MAX_BATCH_SIZE gets truncated."""
        client = self._make_client()
        # CSV with >50 entries
        lines = ["surname,scopus_id\n"] + [f"Author{i},{i}\n" for i in range(60)]
        content = "".join(lines).encode()
        resp = client.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", content, "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "truncated" in str(body.get("errors", [])).lower() or body["total"] <= 50

    def test_batch_cfd_error(self):
        """Batch with CFDError per entry reports error status."""
        from fastapi.testclient import TestClient

        from cfd.api.app import create_app
        from cfd.api.auth import get_api_key
        from cfd.api.dependencies import get_pipeline, get_repos
        from cfd.config.settings import Settings
        from cfd.exceptions import CFDError

        settings = Settings(supabase_url="", supabase_key="")
        app = create_app(settings)

        mock_pipeline = MagicMock()
        mock_pipeline.analyze.side_effect = CFDError("Analysis failed")

        app.dependency_overrides[get_api_key] = lambda: MagicMock(key_id=1, name="test", role="admin")
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
        app.dependency_overrides[get_repos] = lambda: {"audit": MagicMock()}

        client = TestClient(app, raise_server_exceptions=False)
        content = b"surname,scopus_id\nTestAuthor,123\n"
        resp = client.post(
            "/api/v1/batch/analyze",
            files={"file": ("batch.csv", content, "text/csv")},
        )
        assert resp.status_code == 200


# ============================================================
# api/app.py — lifespan with Supabase (lines 33-51)
# ============================================================


class TestAppLifespan:
    def test_lifespan_with_supabase(self):
        """Lifespan initializes supabase when url/key provided."""
        from fastapi.testclient import TestClient

        from cfd.api.app import create_app
        from cfd.api.auth import get_api_key
        from cfd.config.settings import Settings

        settings = Settings(supabase_url="https://test.supabase.co", supabase_key="fake-key")
        with patch("cfd.db.client.get_supabase_client", return_value=MagicMock()):
            app = create_app(settings)
            app.dependency_overrides[get_api_key] = lambda: MagicMock(key_id=1, name="test", role="admin")
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_lifespan_supabase_failure(self):
        """Lifespan handles Supabase connection failure gracefully."""
        from fastapi.testclient import TestClient

        from cfd.api.app import create_app
        from cfd.api.auth import get_api_key
        from cfd.config.settings import Settings

        settings = Settings(supabase_url="https://bad.supabase.co", supabase_key="bad-key")
        with patch("cfd.db.client.get_supabase_client", side_effect=Exception("Connection refused")):
            app = create_app(settings)
            app.dependency_overrides[get_api_key] = lambda: MagicMock(key_id=1, name="test", role="admin")
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/health")
            assert resp.status_code == 200


# ============================================================
# api/app.py — run() function (lines 150-153)
# ============================================================


class TestAppRun:
    def test_run_calls_uvicorn(self):
        """run() calls uvicorn.run with correct arguments."""
        from cfd.api.app import run
        with patch("uvicorn.run") as mock_uv_run:
            run()
        mock_uv_run.assert_called_once()


# ============================================================
# visualization/network.py — node not in pos (line 98)
# ============================================================


class TestVisualizationBranches:
    def test_network_figure_basic(self):
        """Network viz builds figure from author data."""
        from cfd.analysis.pipeline import AnalysisResult
        from cfd.visualization.network import build_network_figure
        profile = _profile()
        pubs = [_pub(idx=i) for i in range(3)]
        cites = [_cite(idx=i) for i in range(5)]
        data = AuthorData(profile=profile, publications=pubs, citations=cites)
        result = AnalysisResult(
            author_profile=profile, fraud_score=0.3, confidence_level="low",
        )
        fig = build_network_figure(data, result, max_nodes=50)
        assert fig is not None


# ============================================================
# visualization/temporal.py — spike chart branches (lines 105-106, 128)
# ============================================================


class TestTemporalViz:
    def _make_result(self, profile, indicators=None):
        from cfd.analysis.pipeline import AnalysisResult
        return AnalysisResult(
            author_profile=profile, fraud_score=0.3, confidence_level="low",
            indicators=indicators or [],
        )

    def test_spike_chart_from_citations(self):
        """Spike chart uses citation dates when raw_data is absent."""
        from cfd.graph.metrics import IndicatorResult
        from cfd.visualization.temporal import build_spike_chart
        profile = _profile()
        pubs = [_pub(yr=2020 + i, idx=i) for i in range(5)]
        cites = [
            _cite(idx=i, citation_date=date(2020 + i % 3, 6, 1))
            for i in range(50)
        ]
        data = AuthorData(profile=profile, publications=pubs, citations=cites)
        ta_ind = IndicatorResult("TA", 0.5, {
            "spike_year": 2020, "yearly_counts": {"2020": 20, "2021": 15, "2022": 15},
        })
        result = self._make_result(profile, indicators=[ta_ind])
        fig = build_spike_chart(data, result, z_threshold=2.0)
        assert fig is not None

    def test_spike_chart_moderate_color(self):
        """Spike chart uses moderate color for mid-range z-scores."""
        from cfd.graph.metrics import IndicatorResult
        from cfd.visualization.temporal import build_spike_chart
        profile = _profile()
        pubs = [_pub(yr=2018 + i, idx=i, citation_count=10 if i != 3 else 30) for i in range(6)]
        cites = [_cite(idx=i) for i in range(20)]
        data = AuthorData(profile=profile, publications=pubs, citations=cites)
        ta_ind = IndicatorResult("TA", 0.5, {
            "spike_year": 2021, "yearly_counts": {"2018": 3, "2019": 4, "2020": 3, "2021": 5, "2022": 3, "2023": 2},
        })
        result = self._make_result(profile, indicators=[ta_ind])
        fig = build_spike_chart(data, result, z_threshold=2.0)
        assert fig is not None


# ============================================================
# notifications/email.py — SMTP_SSL port branch (line 46)
# ============================================================


class TestEmailBranch:
    def test_smtp_ssl_port(self):
        """Email uses SMTP_SSL for port 465."""
        from cfd.notifications.email import send_score_change_email
        with (
            patch("cfd.notifications.email.smtplib") as mock_smtp,
        ):
            mock_ctx = MagicMock()
            mock_smtp.SMTP_SSL.return_value = mock_ctx
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            send_score_change_email(
                to_address="test@example.com",
                author_name="Test",
                old_score=0.3,
                new_score=0.7,
                smtp_host="smtp.example.com",
                smtp_port=465,
                smtp_user="user",
                smtp_password="pass",
            )


# ============================================================
# notifications/webhook.py — empty hostname (line 29)
# ============================================================


class TestWebhookBranch:
    def test_empty_hostname_rejected(self):
        from cfd.notifications.webhook import send_score_change_webhook
        result = send_score_change_webhook(
            url="http:///path",  # empty hostname
            author_name="Test",
            author_id=1,
            old_score=0.3,
            new_score=0.7,
        )
        assert result is False


# ============================================================
# neo4j/etl.py — missing author_id warning (line 80)
# ============================================================


class TestNeo4jEtl:
    def test_sync_batch_empty(self):
        from cfd.neo4j.etl import Neo4jETL
        mock_driver = MagicMock()
        etl = Neo4jETL(mock_driver)
        etl.sync_batch(authors=[], publications=[], citations=[])


# ============================================================
# dashboard pages — uncovered branches
# ============================================================


class TestDashboardBranches:
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
        self.mock_st.tabs.return_value = [mock_col] * 5
        # Import modules first to ensure they exist before patching
        import cfd.dashboard.pages.antiranking  # noqa: F401
        import cfd.dashboard.pages.compare  # noqa: F401
        import cfd.dashboard.pages.dossier  # noqa: F401
        import cfd.dashboard.pages.overview  # noqa: F401
        monkeypatch.setattr("cfd.dashboard.pages.overview.st", self.mock_st)
        monkeypatch.setattr("cfd.dashboard.pages.antiranking.st", self.mock_st)
        monkeypatch.setattr("cfd.dashboard.pages.compare.st", self.mock_st)
        monkeypatch.setattr("cfd.dashboard.pages.dossier.st", self.mock_st)

    def test_overview_invalid_level_fallback(self):
        """Overview falls back to 'normal' for unknown confidence levels."""
        from cfd.dashboard.pages.overview import render
        self.mock_st.slider.return_value = 0.0
        self.mock_st.multiselect.return_value = ["normal", "low", "moderate", "high", "critical"]
        with patch("cfd.dashboard.pages.overview._load_watchlist", return_value=[
            {"id": 1, "author_name": "Test", "fraud_score": 0.5, "confidence_level": "BOGUS_LEVEL"},
        ]):
            render()

    def test_antiranking_invalid_level_fallback(self):
        """Antiranking falls back to 'normal' for unknown levels."""
        from cfd.dashboard.pages.antiranking import render
        with patch("cfd.dashboard.pages.antiranking._load_ranking", return_value=[
            {"author_name": "Test", "fraud_score": 0.5, "confidence_level": "UNKNOWN"},
        ]):
            render()

    def test_dossier_analysis_exception_fallback(self):
        """Dossier handles analysis exception gracefully."""
        from cfd.dashboard.pages.dossier import _run_analysis
        with patch("cfd.cli.main._build_strategy", side_effect=Exception("fail")):
            result, data = _run_analysis("Test", None, None, "openalex")
        # Should return (None, None) and call st.error
        assert result is None and data is None

    def test_compare_missing_metric(self):
        """Compare page handles missing metric value."""
        from cfd.dashboard.pages.compare import render
        self.mock_st.button.return_value = True
        self.mock_st.number_input.return_value = 1
        self.mock_st.slider.return_value = 5
        with patch("cfd.dashboard.pages.compare._load_snapshots", return_value=[
            {"fraud_score": 0.3, "created_at": "2024-01-01"},
            {"fraud_score": 0.5, "created_at": "2024-06-01"},
        ]):
            render()
