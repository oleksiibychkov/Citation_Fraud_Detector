"""Tests for dashboard module — import and structure validation."""

import importlib


def test_dashboard_app_importable():
    """Dashboard app module can be imported."""
    mod = importlib.import_module("cfd.dashboard.app")
    assert hasattr(mod, "main")


def test_dashboard_pages_importable():
    """All dashboard page modules can be imported."""
    for page in ("overview", "dossier", "compare", "antiranking"):
        mod = importlib.import_module(f"cfd.dashboard.views.{page}")
        assert hasattr(mod, "render"), f"{page} missing render()"


def test_dashboard_pages_render_callable():
    """All page render functions are callable."""
    from cfd.dashboard.views import antiranking, compare, dossier, overview

    for mod in (overview, dossier, compare, antiranking):
        assert callable(mod.render)
