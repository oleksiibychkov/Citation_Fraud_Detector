"""Tests for eligibility checking."""

from cfd.analysis.eligibility import check_eligibility
from cfd.config.settings import Settings
from cfd.data.models import AuthorProfile


class TestCheckEligibility:
    def setup_method(self):
        self.settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            scopus_api_key="test-key",
        )

    def test_eligible_author(self):
        profile = AuthorProfile(
            scopus_id="1", surname="X", source_api="test",
            publication_count=50, citation_count=500, h_index=15,
        )
        eligible, reason = check_eligibility(profile, self.settings)
        assert eligible is True
        assert reason == ""

    def test_too_few_publications(self):
        profile = AuthorProfile(
            scopus_id="1", surname="X", source_api="test",
            publication_count=2, citation_count=500, h_index=15,
        )
        eligible, reason = check_eligibility(profile, self.settings)
        assert eligible is False
        assert "publications" in reason

    def test_too_few_citations(self):
        profile = AuthorProfile(
            scopus_id="1", surname="X", source_api="test",
            publication_count=50, citation_count=5, h_index=15,
        )
        eligible, reason = check_eligibility(profile, self.settings)
        assert eligible is False
        assert "citations" in reason

    def test_too_low_h_index(self):
        profile = AuthorProfile(
            scopus_id="1", surname="X", source_api="test",
            publication_count=50, citation_count=500, h_index=1,
        )
        eligible, reason = check_eligibility(profile, self.settings)
        assert eligible is False
        assert "h-index" in reason

    def test_all_below_threshold(self):
        profile = AuthorProfile(
            scopus_id="1", surname="X", source_api="test",
            publication_count=1, citation_count=1, h_index=0,
        )
        eligible, reason = check_eligibility(profile, self.settings)
        assert eligible is False
        assert "publications" in reason
        assert "citations" in reason
        assert "h-index" in reason

    def test_none_values_treated_as_zero(self):
        profile = AuthorProfile(
            scopus_id="1", surname="X", source_api="test",
        )
        eligible, reason = check_eligibility(profile, self.settings)
        assert eligible is False

    def test_at_exact_threshold(self):
        profile = AuthorProfile(
            scopus_id="1", surname="X", source_api="test",
            publication_count=self.settings.min_publications,
            citation_count=self.settings.min_citations,
            h_index=self.settings.min_h_index,
        )
        eligible, reason = check_eligibility(profile, self.settings)
        assert eligible is True
