"""Tests for identity cross-check (§1.3): ORCID vs Scopus ID mismatch detection."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cfd.data.openalex import OpenAlexStrategy
from cfd.data.scopus import ScopusStrategy
from cfd.exceptions import IdentityMismatchError

# ---------------------------------------------------------------------------
# OpenAlex identity cross-check
# ---------------------------------------------------------------------------

class TestOpenAlexIdentityCrossCheck:
    def _make_strategy(self):
        http = MagicMock()
        return OpenAlexStrategy(http_client=http), http

    def test_both_ids_match(self):
        """When both ORCID and Scopus ID resolve to same OpenAlex ID, no error."""
        strategy, http = self._make_strategy()
        author_data = {"id": "https://openalex.org/A1", "display_name": "Test Author"}
        http.get.side_effect = [
            {"results": [author_data]},  # ORCID lookup
            {"results": [author_data]},  # Scopus lookup
        ]
        profile = strategy.fetch_author("Author", scopus_id="12345", orcid="0000-0001-2345-6789")
        assert profile.surname == "Author"

    def test_both_ids_mismatch_raises(self):
        """When ORCID and Scopus ID resolve to different OpenAlex IDs, raise."""
        strategy, http = self._make_strategy()
        data_a = {"id": "https://openalex.org/A1", "display_name": "Author A"}
        data_b = {"id": "https://openalex.org/A2", "display_name": "Author B"}
        http.get.side_effect = [
            {"results": [data_a]},  # ORCID
            {"results": [data_b]},  # Scopus
        ]
        with pytest.raises(IdentityMismatchError, match="different authors"):
            strategy.fetch_author("Author", scopus_id="12345", orcid="0000-0001-2345-6789")

    def test_orcid_found_scopus_not(self):
        """When only ORCID resolves, no error — use ORCID result."""
        strategy, http = self._make_strategy()
        data_orcid = {"id": "https://openalex.org/A1", "display_name": "Test"}
        http.get.side_effect = [
            {"results": [data_orcid]},  # ORCID
            {"results": []},            # Scopus — not found
        ]
        profile = strategy.fetch_author("Test", scopus_id="12345", orcid="0000-0001-2345-6789")
        assert profile.surname == "Test"

    def test_scopus_found_orcid_not(self):
        """When only Scopus ID resolves, no error — use Scopus result."""
        strategy, http = self._make_strategy()
        data_scopus = {"id": "https://openalex.org/A1", "display_name": "Test"}
        http.get.side_effect = [
            {"results": []},             # ORCID — not found
            {"results": [data_scopus]},  # Scopus
        ]
        profile = strategy.fetch_author("Test", scopus_id="12345", orcid="0000-0001-2345-6789")
        assert profile.surname == "Test"

    def test_verify_identity_match_same_id(self):
        """Static method: same OpenAlex ID → no error."""
        OpenAlexStrategy._verify_identity_match(
            {"id": "A1"}, {"id": "A1"}, "orcid", "scopus",
        )

    def test_verify_identity_match_different_id(self):
        """Static method: different OpenAlex IDs → IdentityMismatchError."""
        with pytest.raises(IdentityMismatchError):
            OpenAlexStrategy._verify_identity_match(
                {"id": "A1"}, {"id": "A2"}, "orcid", "scopus",
            )

    def test_verify_identity_match_empty_id(self):
        """Static method: empty IDs → no error (can't compare)."""
        OpenAlexStrategy._verify_identity_match(
            {"id": ""}, {"id": "A2"}, "orcid", "scopus",
        )


# ---------------------------------------------------------------------------
# Scopus identity cross-check
# ---------------------------------------------------------------------------

class TestScopusIdentityCrossCheck:
    def _make_strategy(self):
        http = MagicMock()
        return ScopusStrategy(http_client=http, api_key="test-key"), http

    def test_both_ids_match(self):
        """When Scopus ID and ORCID resolve to same Scopus author, no error."""
        strategy, http = self._make_strategy()
        author_data = {
            "coredata": {"dc:identifier": "AUTHOR_ID:12345"},
            "author-profile": {"preferred-name": {"given-name": "Test", "surname": "Author"}},
        }
        # _fetch_by_scopus_id returns author_data directly
        # _fetch_by_orcid searches then fetches by ID
        http.get.side_effect = [
            {"author-retrieval-response": [author_data]},  # by scopus_id
            {"search-results": {"entry": [{"dc:identifier": "AUTHOR_ID:12345"}]}},  # ORCID search
            {"author-retrieval-response": [author_data]},  # fetch by resolved ID
        ]
        profile = strategy.fetch_author("Author", scopus_id="12345", orcid="0000-0001-2345-6789")
        assert profile.surname == "Author"

    def test_both_ids_mismatch_raises(self):
        """When Scopus ID and ORCID resolve to different Scopus authors, raise."""
        strategy, http = self._make_strategy()
        data_scopus = {
            "coredata": {"dc:identifier": "AUTHOR_ID:12345"},
            "author-profile": {"preferred-name": {"given-name": "A", "surname": "X"}},
        }
        data_orcid = {
            "coredata": {"dc:identifier": "AUTHOR_ID:99999"},
            "author-profile": {"preferred-name": {"given-name": "B", "surname": "Y"}},
        }
        http.get.side_effect = [
            {"author-retrieval-response": [data_scopus]},  # by scopus_id
            {"search-results": {"entry": [{"dc:identifier": "AUTHOR_ID:99999"}]}},  # ORCID search
            {"author-retrieval-response": [data_orcid]},  # fetch by resolved ID
        ]
        with pytest.raises(IdentityMismatchError, match="different authors"):
            strategy.fetch_author("Author", scopus_id="12345", orcid="0000-0001-2345-6789")

    def test_verify_identity_match_same(self):
        """Static method: same Scopus ID → no error."""
        ScopusStrategy._verify_identity_match(
            {"coredata": {"dc:identifier": "AUTHOR_ID:123"}},
            {"coredata": {"dc:identifier": "AUTHOR_ID:123"}},
            "123", "orcid",
        )

    def test_verify_identity_match_different(self):
        """Static method: different Scopus IDs → IdentityMismatchError."""
        with pytest.raises(IdentityMismatchError):
            ScopusStrategy._verify_identity_match(
                {"coredata": {"dc:identifier": "AUTHOR_ID:123"}},
                {"coredata": {"dc:identifier": "AUTHOR_ID:456"}},
                "123", "orcid",
            )
