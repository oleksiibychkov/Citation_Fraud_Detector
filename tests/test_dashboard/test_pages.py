"""Tests for Streamlit dashboard pages with mocked st.* calls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_streamlit(monkeypatch):
    """Mock all streamlit functions used by dashboard pages."""
    mock_st = MagicMock()
    # st.columns returns the right number of MagicMock context managers based on input
    mock_col = MagicMock()
    mock_col.__enter__ = MagicMock(return_value=mock_col)
    mock_col.__exit__ = MagicMock(return_value=False)

    def _columns(spec):
        n = spec if isinstance(spec, int) else len(spec)
        return [MagicMock(__enter__=MagicMock(return_value=mock_col), __exit__=MagicMock(return_value=False))
                for _ in range(n)]

    mock_st.columns.side_effect = _columns
    mock_st.tabs.return_value = [mock_col, mock_col, mock_col, mock_col]
    mock_st.slider.return_value = 0.0
    mock_st.number_input.return_value = 1
    mock_st.button.return_value = True
    mock_st.text_input.return_value = ""
    mock_st.selectbox.return_value = "auto"
    mock_st.checkbox.return_value = False
    mock_st.multiselect.return_value = ["normal", "low", "moderate", "high", "critical"]
    mock_st.session_state = {"lang": "ua"}
    mock_st.spinner.return_value.__enter__ = MagicMock()
    mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr("cfd.dashboard.pages.overview.st", mock_st)
    monkeypatch.setattr("cfd.dashboard.pages.antiranking.st", mock_st)
    monkeypatch.setattr("cfd.dashboard.pages.compare.st", mock_st)
    monkeypatch.setattr("cfd.dashboard.pages.dossier.st", mock_st)
    monkeypatch.setattr("cfd.dashboard.disclaimer.st", mock_st)
    return mock_st


# ============================================================
# disclaimer.py
# ============================================================


class TestDisclaimer:
    def test_render_disclaimer(self):
        from cfd.dashboard.disclaimer import render_disclaimer
        render_disclaimer()


# ============================================================
# overview.py
# ============================================================


class TestOverview:
    def test_render_with_entries(self, _mock_streamlit):
        from cfd.dashboard.pages.overview import render

        with patch("cfd.dashboard.pages.overview._load_watchlist") as mock_load:
            mock_load.return_value = [
                {"author_name": "Author A", "fraud_score": 0.8, "confidence_level": "high", "reason": "test"},
                {"author_name": "Author B", "fraud_score": 0.2, "confidence_level": "low", "reason": "—"},
            ]
            render()
        _mock_streamlit.header.assert_called()

    def test_render_empty(self, _mock_streamlit):
        from cfd.dashboard.pages.overview import render

        with patch("cfd.dashboard.pages.overview._load_watchlist", return_value=[]):
            render()
        _mock_streamlit.info.assert_called()

    def test_render_no_match_filter(self, _mock_streamlit):
        _mock_streamlit.slider.return_value = 0.99
        from cfd.dashboard.pages.overview import render

        with patch("cfd.dashboard.pages.overview._load_watchlist") as mock_load:
            mock_load.return_value = [
                {"author_name": "A", "fraud_score": 0.1, "confidence_level": "normal"},
            ]
            render()
        _mock_streamlit.warning.assert_called()

    def test_load_watchlist_no_supabase(self):
        from cfd.dashboard.pages.overview import _load_watchlist

        with patch("cfd.config.settings.Settings", return_value=MagicMock(supabase_url="", supabase_key="")):
            result = _load_watchlist()
        assert result == []

    def test_load_watchlist_with_data(self):
        from cfd.dashboard.pages.overview import _load_watchlist

        mock_settings = MagicMock(supabase_url="https://test.co", supabase_key="key")
        mock_client = MagicMock()
        mock_watchlist = MagicMock()
        mock_watchlist.get_active.return_value = [{"author_id": 1, "reason": "test"}]
        mock_author = MagicMock()
        mock_author.get_by_id.return_value = {"full_name": "Test Author", "surname": "Test"}
        mock_score = MagicMock()
        mock_score.get_latest_by_author.return_value = {"score": 0.5, "confidence_level": "moderate"}

        with patch("cfd.config.settings.Settings", return_value=mock_settings), \
             patch("cfd.db.client.get_supabase_client", return_value=mock_client), \
             patch("cfd.db.repositories.watchlist.WatchlistRepository", return_value=mock_watchlist), \
             patch("cfd.db.repositories.authors.AuthorRepository", return_value=mock_author), \
             patch("cfd.db.repositories.fraud_scores.FraudScoreRepository", return_value=mock_score):
            result = _load_watchlist()
        assert len(result) == 1
        assert result[0]["author_name"] == "Test Author"

    def test_load_watchlist_exception(self):
        from cfd.dashboard.pages.overview import _load_watchlist

        with patch("cfd.config.settings.Settings", side_effect=Exception("fail")):
            result = _load_watchlist()
        assert result == []

    def test_render_invalid_level(self, _mock_streamlit):
        """Entry with invalid level should fall back to 'normal'."""
        from cfd.dashboard.pages.overview import render

        with patch("cfd.dashboard.pages.overview._load_watchlist") as mock_load:
            mock_load.return_value = [
                {"author_name": "X", "fraud_score": 0.3, "confidence_level": "INVALID_LEVEL", "reason": "—"},
            ]
            render()


# ============================================================
# antiranking.py
# ============================================================


class TestAntiranking:
    def test_render_with_entries(self, _mock_streamlit):
        from cfd.dashboard.pages.antiranking import render

        with patch("cfd.dashboard.pages.antiranking._load_ranking") as mock_load:
            mock_load.return_value = [
                {"author_name": "A", "fraud_score": 0.8, "confidence_level": "high",
                 "h_index": 15, "citation_count": 300, "publication_count": 40},
            ]
            render()
        _mock_streamlit.header.assert_called()

    def test_render_empty(self, _mock_streamlit):
        from cfd.dashboard.pages.antiranking import render

        with patch("cfd.dashboard.pages.antiranking._load_ranking", return_value=[]):
            render()
        _mock_streamlit.info.assert_called()

    def test_load_ranking_no_supabase(self):
        from cfd.dashboard.pages.antiranking import _load_ranking

        with patch("cfd.config.settings.Settings",
                    return_value=MagicMock(supabase_url="", supabase_key="")):
            result = _load_ranking()
        assert result == []

    def test_load_ranking_with_data(self):
        from cfd.dashboard.pages.antiranking import _load_ranking

        mock_settings = MagicMock(supabase_url="https://t.co", supabase_key="k")
        mock_client = MagicMock()
        mock_score_repo = MagicMock()
        mock_score_repo.get_all_ranked.return_value = [{"author_id": 1, "score": 0.5, "confidence_level": "moderate"}]
        mock_author_repo = MagicMock()
        mock_author_repo.get_by_id.return_value = {"full_name": "Author", "h_index": 10}

        with patch("cfd.config.settings.Settings", return_value=mock_settings), \
             patch("cfd.db.client.get_supabase_client", return_value=mock_client), \
             patch("cfd.db.repositories.fraud_scores.FraudScoreRepository", return_value=mock_score_repo), \
             patch("cfd.db.repositories.authors.AuthorRepository", return_value=mock_author_repo):
            result = _load_ranking()
        assert len(result) == 1

    def test_load_ranking_exception(self):
        from cfd.dashboard.pages.antiranking import _load_ranking

        with patch("cfd.config.settings.Settings", side_effect=Exception("fail")):
            result = _load_ranking()
        assert result == []

    def test_export_csv(self, _mock_streamlit):
        from cfd.dashboard.pages.antiranking import _export_csv
        entries = [
            {"author_name": "A", "fraud_score": 0.8, "confidence_level": "high",
             "h_index": 15, "citation_count": 300, "publication_count": 40},
        ]
        _export_csv(entries)
        _mock_streamlit.download_button.assert_called_once()

    def test_render_ascending(self, _mock_streamlit):
        _mock_streamlit.checkbox.return_value = True
        from cfd.dashboard.pages.antiranking import render

        with patch("cfd.dashboard.pages.antiranking._load_ranking") as mock_load:
            mock_load.return_value = [
                {"author_name": "A", "fraud_score": 0.2, "confidence_level": "low",
                 "h_index": 5, "citation_count": 50, "publication_count": 10},
                {"author_name": "B", "fraud_score": 0.8, "confidence_level": "high",
                 "h_index": 20, "citation_count": 500, "publication_count": 60},
            ]
            render()


# ============================================================
# compare.py
# ============================================================


class TestCompare:
    def test_render_no_button(self, _mock_streamlit):
        _mock_streamlit.button.return_value = False
        from cfd.dashboard.pages.compare import render
        render()

    def test_render_no_snapshots(self, _mock_streamlit):
        from cfd.dashboard.pages.compare import render

        with patch("cfd.dashboard.pages.compare._load_snapshots", return_value=[]):
            render()
        _mock_streamlit.info.assert_called()

    def test_render_one_snapshot(self, _mock_streamlit):
        from cfd.dashboard.pages.compare import render

        with patch("cfd.dashboard.pages.compare._load_snapshots") as mock_load:
            mock_load.return_value = [{"fraud_score": 0.3, "h_index": 10}]
            render()
        _mock_streamlit.warning.assert_called()

    def test_render_two_snapshots(self, _mock_streamlit):
        from cfd.dashboard.pages.compare import render

        with patch("cfd.dashboard.pages.compare._load_snapshots") as mock_load:
            mock_load.return_value = [
                {"fraud_score": 0.5, "h_index": 15, "citation_count": 300,
                 "publication_count": 40, "algorithm_version": "5.0.0"},
                {"fraud_score": 0.3, "h_index": 10, "citation_count": 200,
                 "publication_count": 30, "algorithm_version": "4.0.0"},
            ]
            render()
        # Should show algorithm version warning
        _mock_streamlit.warning.assert_called()

    def test_render_same_algo_version(self, _mock_streamlit):
        from cfd.dashboard.pages.compare import render

        with patch("cfd.dashboard.pages.compare._load_snapshots") as mock_load:
            mock_load.return_value = [
                {"fraud_score": 0.5, "h_index": 15, "citation_count": 300,
                 "publication_count": 40, "algorithm_version": "5.0.0"},
                {"fraud_score": 0.3, "h_index": 10, "citation_count": 200,
                 "publication_count": 30, "algorithm_version": "5.0.0"},
            ]
            render()

    def test_load_snapshots_exception(self, _mock_streamlit):
        from cfd.dashboard.pages.compare import _load_snapshots

        with patch("cfd.config.settings.Settings", side_effect=Exception("fail")):
            result = _load_snapshots(1, 5)
        assert result == []

    def test_load_snapshots_success(self):
        from cfd.dashboard.pages.compare import _load_snapshots

        mock_repo = MagicMock()
        mock_repo.get_by_author_id.return_value = [{"fraud_score": 0.5}]
        with patch("cfd.config.settings.Settings", return_value=MagicMock()), \
             patch("cfd.db.client.get_supabase_client", return_value=MagicMock()), \
             patch("cfd.db.repositories.snapshots.SnapshotRepository", return_value=mock_repo):
            result = _load_snapshots(1, 5)
        assert len(result) == 1

    def test_show_single(self, _mock_streamlit):
        from cfd.dashboard.pages.compare import _show_single
        _show_single({"fraud_score": 0.3, "h_index": 10})

    def test_render_timeline(self, _mock_streamlit):
        from cfd.dashboard.pages.compare import _render_timeline
        snapshots = [
            {"fraud_score": 0.5, "snapshot_date": "2024-01-15"},
            {"fraud_score": 0.3, "snapshot_date": "2024-01-01"},
        ]
        _render_timeline(snapshots)
        _mock_streamlit.plotly_chart.assert_called()

    def test_render_non_numeric_metric(self, _mock_streamlit):
        """Metric with non-numeric value triggers ValueError branch."""
        from cfd.dashboard.pages.compare import render

        with patch("cfd.dashboard.pages.compare._load_snapshots") as mock_load:
            mock_load.return_value = [
                {"fraud_score": "bad", "h_index": 15, "citation_count": 300,
                 "publication_count": 40, "algorithm_version": "5.0.0"},
                {"fraud_score": "bad", "h_index": 10, "citation_count": 200,
                 "publication_count": 30, "algorithm_version": "5.0.0"},
            ]
            render()


# ============================================================
# dossier.py
# ============================================================


class TestDossier:
    def test_render_no_button(self, _mock_streamlit):
        _mock_streamlit.button.return_value = False
        from cfd.dashboard.pages.dossier import render
        render()

    def test_render_no_author_name(self, _mock_streamlit):
        _mock_streamlit.text_input.return_value = ""
        from cfd.dashboard.pages.dossier import render
        render()
        _mock_streamlit.error.assert_called()

    def test_render_no_ids(self, _mock_streamlit):
        # First call returns author name, next two return ""
        _mock_streamlit.text_input.side_effect = ["TestAuthor", "", ""]
        from cfd.dashboard.pages.dossier import render
        render()

    def test_render_analysis_fails(self, _mock_streamlit):
        _mock_streamlit.text_input.side_effect = ["TestAuthor", "123", ""]
        from cfd.dashboard.pages.dossier import render

        with patch("cfd.dashboard.pages.dossier._run_analysis", return_value=(None, None)):
            render()
        _mock_streamlit.error.assert_called()

    def test_render_full_analysis(self, _mock_streamlit):
        from cfd.analysis.pipeline import AnalysisResult
        from cfd.data.models import AuthorData, AuthorProfile
        from cfd.graph.metrics import IndicatorResult

        _mock_streamlit.text_input.side_effect = ["TestAuthor", "123", ""]
        profile = AuthorProfile(
            scopus_id="123", surname="Test", full_name="Test Author",
            source_api="test", h_index=20, publication_count=50, citation_count=500,
        )
        result = AnalysisResult(
            author_profile=profile,
            indicators=[IndicatorResult("SCR", 0.15, {})],
            fraud_score=0.35, confidence_level="low",
            triggered_indicators=["SCR"],
        )
        author_data = AuthorData(profile=profile, publications=[], citations=[])

        from cfd.dashboard.pages.dossier import render

        with patch("cfd.dashboard.pages.dossier._run_analysis", return_value=(result, author_data)):
            render()

    def test_run_analysis_success(self, _mock_streamlit):
        from cfd.dashboard.pages.dossier import _run_analysis

        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.author_profile = MagicMock()
        mock_pipeline.analyze.return_value = mock_result
        mock_strategy = MagicMock()
        mock_strategy.collect.return_value = MagicMock()

        with patch("cfd.config.settings.Settings", return_value=MagicMock()), \
             patch("cfd.cli.main._build_strategy", return_value=mock_strategy), \
             patch("cfd.cli.main._build_pipeline", return_value=mock_pipeline):
            result, data = _run_analysis("Test", "123", "", "auto")
        assert result is not None

    def test_run_analysis_exception(self, _mock_streamlit):
        from cfd.dashboard.pages.dossier import _run_analysis

        with patch("cfd.config.settings.Settings", side_effect=Exception("fail")):
            result, data = _run_analysis("Test", "123", "", "auto")
        assert result is None

    def test_render_visualizations(self, _mock_streamlit):
        from cfd.dashboard.pages.dossier import _render_visualizations
        mock_data = MagicMock()
        mock_result = MagicMock()
        _render_visualizations(mock_data, mock_result)


# ============================================================
# app.py — main routing
# ============================================================


class TestDashboardApp:
    def test_main_overview(self, monkeypatch):
        mock_st = MagicMock()
        mock_st.sidebar.radio.return_value = "Overview"
        mock_st.sidebar.selectbox.return_value = "ua"
        mock_st.session_state = {}
        monkeypatch.setattr("cfd.dashboard.app.st", mock_st)

        with patch("cfd.dashboard.pages.overview.render") as mock_render:
            from cfd.dashboard.app import main
            main()
            mock_render.assert_called_once()

    def test_main_dossier(self, monkeypatch):
        mock_st = MagicMock()
        mock_st.sidebar.radio.return_value = "Author Dossier"
        mock_st.sidebar.selectbox.return_value = "en"
        mock_st.session_state = {}
        monkeypatch.setattr("cfd.dashboard.app.st", mock_st)

        with patch("cfd.dashboard.pages.dossier.render") as mock_render:
            from cfd.dashboard.app import main
            main()
            mock_render.assert_called_once()

    def test_main_compare(self, monkeypatch):
        mock_st = MagicMock()
        mock_st.sidebar.radio.return_value = "Snapshot Compare"
        mock_st.sidebar.selectbox.return_value = "ua"
        mock_st.session_state = {}
        monkeypatch.setattr("cfd.dashboard.app.st", mock_st)

        with patch("cfd.dashboard.pages.compare.render") as mock_render:
            from cfd.dashboard.app import main
            main()
            mock_render.assert_called_once()

    def test_main_antiranking(self, monkeypatch):
        mock_st = MagicMock()
        mock_st.sidebar.radio.return_value = "Anti-Ranking"
        mock_st.sidebar.selectbox.return_value = "ua"
        mock_st.session_state = {}
        monkeypatch.setattr("cfd.dashboard.app.st", mock_st)

        with patch("cfd.dashboard.pages.antiranking.render") as mock_render:
            from cfd.dashboard.app import main
            main()
            mock_render.assert_called_once()
