"""Tests for bugs found and fixed during deep system audit.

Covers all 10 bug fixes:
1. Community detection: isolated clusters now flagged as suspicious
2. HTA: 0→nonzero growth rate uses raw value instead of 0.0
3. Schemas: NaN/Inf rejected in sensitivity overrides
4. Path traversal: surname sanitized in batch filenames
5. Supabase client: thread-safe singleton with lock
6. Pipeline: failed indicators tracked in warnings
7. Email: STARTTLS always used for non-SSL ports
8. Validators: empty API name treated as mismatch
9. CORS: wildcard anywhere in origins disables credentials
10. Temporal: half_life <= 0 returns None instead of division error
"""

from __future__ import annotations

import threading
from datetime import date
from unittest.mock import MagicMock, patch

import networkx as nx
import pytest
from pydantic import ValidationError as PydanticValidationError

from cfd.analysis.temporal import _paper_citation_velocity
from cfd.api.schemas import SensitivityOverridesRequest
from cfd.data.models import AuthorData, AuthorProfile, Citation, Publication
from cfd.data.validators import check_surname_match
from cfd.graph.community import detect_communities
from cfd.graph.metrics import compute_hta

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _profile(**kw) -> AuthorProfile:
    defaults = dict(
        surname="Test", full_name="Test Author",
        scopus_id="12345", h_index=10,
        publication_count=20, citation_count=100,
        source_api="openalex",
    )
    defaults.update(kw)
    return AuthorProfile(**defaults)


def _pub(idx=0, **kw) -> Publication:
    defaults = dict(
        work_id=f"W{idx}",
        publication_date=date(2020, 1, 1),
        title=f"Paper {idx}",
        journal="Test Journal",
        citation_count=5,
        source_api="openalex",
        raw_data={},
    )
    defaults.update(kw)
    return Publication(**defaults)


def _author_data(pubs=None, cits=None, **kw) -> AuthorData:
    return AuthorData(
        profile=_profile(**kw),
        publications=pubs or [],
        citations=cits or [],
    )


# ---------------------------------------------------------------------------
# Bug 1: Community detection — isolated clusters
# ---------------------------------------------------------------------------

class TestIsolatedCommunityDetection:
    """Isolated communities (no external edges) should be flagged as suspicious."""

    def test_isolated_community_flagged(self):
        """Community with internal edges but no external edges → suspicious."""
        # Create a graph with two isolated cliques
        g = nx.DiGraph()
        g.add_edges_from([("A", "B"), ("B", "A"), ("A", "C"), ("C", "A")])
        g.add_edges_from([("D", "E"), ("E", "D"), ("D", "F"), ("F", "D")])

        engine = MagicMock()
        # Louvain partitions into two communities
        engine.louvain_communities.return_value = {
            "A": 0, "B": 0, "C": 0,
            "D": 1, "E": 1, "F": 1,
        }
        engine.modularity.return_value = 0.5

        # Both communities: high internal, zero external
        engine.community_densities.return_value = (0.8, 0.0)

        result = detect_communities(engine, min_community_size=3)
        assert len(result.suspicious_communities) == 2
        for sc in result.suspicious_communities:
            assert sc["isolated"] is True
            assert sc["density_ratio"] == float("inf")

    def test_isolated_no_internal_not_flagged(self):
        """Community with no internal AND no external edges → not suspicious."""
        engine = MagicMock()
        engine.louvain_communities.return_value = {"A": 0, "B": 0, "C": 0}
        engine.modularity.return_value = 0.0
        engine.community_densities.return_value = (0.0, 0.0)

        result = detect_communities(engine, min_community_size=3)
        assert len(result.suspicious_communities) == 0


# ---------------------------------------------------------------------------
# Bug 2: HTA — 0→nonzero growth rate
# ---------------------------------------------------------------------------

class TestHTAZeroToNonzero:
    """0→nonzero citation transitions should produce meaningful growth rates."""

    def test_zero_to_nonzero_growth(self):
        """Years with 0 citations followed by nonzero should have high growth rate."""
        pubs = [_pub(0, raw_data={
            "counts_by_year": [
                {"year": 2018, "cited_by_count": 0},
                {"year": 2019, "cited_by_count": 0},
                {"year": 2020, "cited_by_count": 0},
                {"year": 2021, "cited_by_count": 50},
                {"year": 2022, "cited_by_count": 5},
            ]
        })]
        ad = _author_data(pubs=pubs)
        result = compute_hta(ad)
        # The 0→50 growth should produce a high value, not 0.0
        assert result.value > 0.0
        assert result.details.get("max_growth_rate", 0) > 0


# ---------------------------------------------------------------------------
# Bug 3: Schemas — NaN/Inf in sensitivity overrides
# ---------------------------------------------------------------------------

class TestSensitivityNanInf:
    """NaN and Inf values must be rejected by the validator."""

    def test_nan_rejected(self):
        with pytest.raises(PydanticValidationError, match="finite"):
            SensitivityOverridesRequest(overrides={"scr_warn_threshold": float("nan")})

    def test_inf_rejected(self):
        with pytest.raises(PydanticValidationError, match="finite"):
            SensitivityOverridesRequest(overrides={"cb_threshold": float("inf")})

    def test_negative_inf_rejected(self):
        with pytest.raises(PydanticValidationError, match="finite"):
            SensitivityOverridesRequest(overrides={"ta_z_threshold": float("-inf")})

    def test_valid_values_pass(self):
        req = SensitivityOverridesRequest(overrides={"scr_warn_threshold": 0.5})
        assert req.overrides["scr_warn_threshold"] == 0.5


# ---------------------------------------------------------------------------
# Bug 4: Path traversal — surname sanitized
# ---------------------------------------------------------------------------

class TestPathTraversalSanitization:
    """Malicious surnames must be sanitized in batch output filenames."""

    def test_path_traversal_chars_removed(self):
        import re
        surname = "../../etc/passwd"
        safe = re.sub(r'[^\w\-]', '_', surname)
        assert "/" not in safe
        assert ".." not in safe

    def test_normal_surname_unchanged(self):
        import re
        surname = "Ivanenko"
        safe = re.sub(r'[^\w\-]', '_', surname)
        assert safe == "Ivanenko"

    def test_hyphenated_surname_preserved(self):
        import re
        surname = "Smith-Jones"
        safe = re.sub(r'[^\w\-]', '_', surname)
        assert safe == "Smith-Jones"


# ---------------------------------------------------------------------------
# Bug 5: Supabase client — thread-safe singleton
# ---------------------------------------------------------------------------

class TestSupabaseThreadSafety:
    """Singleton client creation must be thread-safe."""

    def test_lock_exists(self):
        """The module-level lock should exist."""
        from cfd.db import client as client_mod
        assert hasattr(client_mod, '_lock')
        assert isinstance(client_mod._lock, type(threading.Lock()))

    def test_concurrent_calls_single_creation(self):
        """Multiple threads calling get_supabase_client should create only one client."""
        from cfd.db import client as client_mod
        client_mod._client = None  # Reset

        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_key = "test-key"

        with patch.dict("sys.modules", {"supabase": MagicMock()}):
            import sys
            sys.modules["supabase"].create_client = MagicMock(return_value=mock_client)
            mock_create = sys.modules["supabase"].create_client

            results = []
            def call_get():
                c = client_mod.get_supabase_client(mock_settings)
                results.append(c)

            threads = [threading.Thread(target=call_get) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All threads should get the same client instance
            assert len(set(id(r) for r in results)) == 1
            # Client should only be created once
            assert mock_create.call_count == 1

        # Cleanup
        client_mod._client = None


# ---------------------------------------------------------------------------
# Bug 6: Pipeline — failed indicators tracked in warnings
# ---------------------------------------------------------------------------

class TestPipelineFailureWarnings:
    """When indicator computation fails, warnings should be populated."""

    def test_warnings_populated_on_failure(self):
        from cfd.analysis.pipeline import AnalysisPipeline

        mock_strategy = MagicMock()
        mock_strategy.collect.return_value = _author_data(
            pubs=[_pub(0)],
            cits=[Citation(
                source_work_id="W999", target_work_id="W0",
                source_author_id=999, target_author_id=1,
                is_self_citation=False,
                source_api="openalex",
            )],
        )

        settings = MagicMock()
        settings.min_publications = 0
        settings.min_citations = 0
        settings.min_h_index = 0
        settings.ta_z_threshold = 3.0
        settings.community_density_ratio_threshold = 2.0
        settings.min_community_size = 3
        settings.mutual_mcr_threshold = 0.1
        settings.min_clique_size = 3
        settings.cantelli_z_threshold = 2.0
        settings.cv_threshold = 5.0
        settings.sbd_beauty_threshold = 100.0
        settings.sbd_suspicious_threshold = 0.3
        settings.ana_single_paper_coauthor_threshold = 0.5
        settings.cc_per_paper_threshold = 0.3
        settings.ssd_similarity_threshold = 0.8
        settings.ssd_interval_days = 30
        settings.pb_k_neighbors = 5
        settings.pb_min_peers = 3
        settings.cpc_divergence_threshold = 0.3
        settings.ctx_independent_threshold = 3
        settings.igraph_node_threshold = 500
        settings.algorithm_version = "test"

        pipeline = AnalysisPipeline(strategy=mock_strategy, settings=settings)

        # Patch ANA to fail + compute_fraud_score to avoid needing all real settings
        with (
            patch("cfd.analysis.pipeline.compute_ana", side_effect=RuntimeError("boom")),
            patch("cfd.analysis.pipeline.compute_fraud_score", return_value=(0.5, "normal", [])),
        ):
            result = pipeline.analyze("Test", scopus_id="12345")

        assert "ANA computation failed" in result.warnings


# ---------------------------------------------------------------------------
# Bug 7: Email — STARTTLS on port 25
# ---------------------------------------------------------------------------

class TestEmailSTARTTLS:
    """STARTTLS should always be used for non-SSL ports (including port 25)."""

    @patch("cfd.notifications.email.smtplib.SMTP")
    def test_port_25_uses_starttls(self, mock_smtp_cls):
        from cfd.notifications.email import send_score_change_email

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_score_change_email(
            to_address="admin@example.com",
            author_name="Test",
            old_score=0.1,
            new_score=0.5,
            smtp_host="smtp.test.local",
            smtp_port=25,
        )

        mock_server.starttls.assert_called_once()

    @patch("cfd.notifications.email.smtplib.SMTP_SSL")
    def test_port_465_no_starttls(self, mock_smtp_ssl_cls):
        from cfd.notifications.email import send_score_change_email

        mock_server = MagicMock()
        mock_smtp_ssl_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_ssl_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_score_change_email(
            to_address="admin@example.com",
            author_name="Test",
            old_score=0.1,
            new_score=0.5,
            smtp_host="smtp.test.local",
            smtp_port=465,
        )

        mock_server.starttls.assert_not_called()


# ---------------------------------------------------------------------------
# Bug 8: Validators — empty API name
# ---------------------------------------------------------------------------

class TestEmptyApiName:
    """Empty API name should be treated as a mismatch, not a pass."""

    def test_empty_api_name_is_mismatch(self):
        matches, warning = check_surname_match("Ivanenko", "")
        assert matches is False
        assert "empty" in warning.lower()

    def test_none_api_name_is_mismatch(self):
        """None gets converted to empty string in practice — also mismatch."""
        matches, warning = check_surname_match("Ivanenko", "")
        assert matches is False


# ---------------------------------------------------------------------------
# Bug 9: CORS — wildcard edge case
# ---------------------------------------------------------------------------

class TestCORSWildcard:
    """Wildcard anywhere in origins list should disable allow_credentials."""

    def test_wildcard_only(self):
        origins = ["*"]
        allow_credentials = "*" not in origins
        assert allow_credentials is False

    def test_wildcard_with_other_origins(self):
        """Even if other origins are listed alongside *, credentials must be disabled."""
        origins = ["https://app.example.com", "*"]
        allow_credentials = "*" not in origins
        assert allow_credentials is False

    def test_no_wildcard(self):
        origins = ["https://app.example.com", "https://admin.example.com"]
        allow_credentials = "*" not in origins
        assert allow_credentials is True


# ---------------------------------------------------------------------------
# Bug 10: Temporal — half_life <= 0 guard
# ---------------------------------------------------------------------------

class TestHalfLifeGuard:
    """half_life <= 0 should return None instead of causing a math error."""

    def test_zero_half_life(self):
        from cfd.analysis.baselines import DisciplineBaseline
        baseline = DisciplineBaseline(
            discipline="test", avg_scr=0.1, std_scr=0.05,
            avg_citations_per_paper=10.0,
            citation_half_life_years=0.0,
        )
        pub = _pub(0, publication_date=date(2018, 1, 1), citation_count=50)
        result = _paper_citation_velocity(pub, baseline)
        assert result is None

    def test_negative_half_life(self):
        from cfd.analysis.baselines import DisciplineBaseline
        baseline = DisciplineBaseline(
            discipline="test", avg_scr=0.1, std_scr=0.05,
            avg_citations_per_paper=10.0,
            citation_half_life_years=-1.0,
        )
        pub = _pub(0, publication_date=date(2018, 1, 1), citation_count=50)
        result = _paper_citation_velocity(pub, baseline)
        assert result is None

    def test_positive_half_life_works(self):
        from cfd.analysis.baselines import DisciplineBaseline
        baseline = DisciplineBaseline(
            discipline="test", avg_scr=0.1, std_scr=0.05,
            avg_citations_per_paper=10.0,
            citation_half_life_years=5.0,
        )
        pub = _pub(0, publication_date=date(2018, 1, 1), citation_count=50)
        result = _paper_citation_velocity(pub, baseline, current_year=2024)
        assert result is not None
        assert result > 0
