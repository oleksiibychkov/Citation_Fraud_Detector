"""Tests for CRIS integration endpoints (§6.4)."""

from __future__ import annotations

from cfd.api.routers.cris import (
    ConverisSyncBody,
    PureWebhookBody,
    VIVOQueryBody,
    _extract_converis_author,
    _extract_pure_author,
    _extract_vivo_author,
)

# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------


class TestExtractPureAuthor:
    def test_extracts_author(self):
        body = PureWebhookBody(
            event="new_researcher",
            researcher={"lastName": "Smith", "firstName": "John", "orcid": "0000-0001-2345-6789"},
        )
        result = _extract_pure_author(body)
        assert result is not None
        assert result.surname == "Smith"
        assert result.given_name == "John"
        assert result.orcid == "0000-0001-2345-6789"

    def test_empty_researcher(self):
        body = PureWebhookBody(event="test", researcher={})
        assert _extract_pure_author(body) is None


class TestExtractConverisAuthor:
    def test_extracts_author(self):
        body = ConverisSyncBody(
            action="sync",
            person={"familyName": "Müller", "givenName": "Anna", "scopusAuthorId": "12345"},
        )
        result = _extract_converis_author(body)
        assert result is not None
        assert result.surname == "Müller"
        assert result.scopus_id == "12345"

    def test_empty_person(self):
        body = ConverisSyncBody(action="sync", person={})
        assert _extract_converis_author(body) is None


class TestExtractVIVOAuthor:
    def test_extracts_author(self):
        body = VIVOQueryBody(
            sparql="SELECT ...",
            results=[{"familyName": "Garcia", "givenName": "Carlos", "orcid": "0000-0002-1234-5678"}],
        )
        result = _extract_vivo_author(body)
        assert result is not None
        assert result.surname == "Garcia"
        assert result.orcid == "0000-0002-1234-5678"

    def test_empty_results(self):
        body = VIVOQueryBody(sparql="SELECT ...", results=[])
        assert _extract_vivo_author(body) is None


# ---------------------------------------------------------------------------
# Endpoint integration tests
# ---------------------------------------------------------------------------


class TestPureWebhookEndpoint:
    def test_pure_with_known_author(self, client_admin, mock_repos):
        mock_repos["author"].get_by_scopus_id.return_value = {"id": 42, "surname": "Smith"}
        resp = client_admin.post("/api/v1/cris/pure/webhook", json={
            "event": "new_researcher",
            "researcher": {"lastName": "Smith", "scopusId": "12345"},
        })
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] in ("accepted", "added_to_watchlist")
        assert data["author_id"] == 42
        mock_repos["watchlist"].add.assert_called_once()
        mock_repos["audit"].log.assert_called()

    def test_pure_author_not_found(self, client_admin, mock_repos):
        mock_repos["author"].get_by_scopus_id.return_value = None
        mock_repos["author"].get_by_orcid.return_value = None
        resp = client_admin.post("/api/v1/cris/pure/webhook", json={
            "event": "new_researcher",
            "researcher": {"lastName": "Unknown", "orcid": "0000-0001-0000-0000"},
        })
        assert resp.status_code == 202
        assert resp.json()["status"] in ("accepted", "author_not_found")

    def test_pure_empty_body(self, client_admin):
        resp = client_admin.post("/api/v1/cris/pure/webhook", json={
            "event": "test", "researcher": {},
        })
        assert resp.status_code == 202
        assert "No author data" in resp.json().get("message", "")


class TestConverisSyncEndpoint:
    def test_converis_with_known_author(self, client_admin, mock_repos):
        mock_repos["author"].get_by_scopus_id.return_value = {"id": 10, "surname": "Müller"}
        resp = client_admin.post("/api/v1/cris/converis/sync", json={
            "action": "sync",
            "person": {"familyName": "Müller", "scopusAuthorId": "99999"},
        })
        assert resp.status_code == 202
        assert resp.json()["status"] in ("accepted", "added_to_watchlist")
        mock_repos["watchlist"].add.assert_called_once()

    def test_converis_empty_person(self, client_admin):
        resp = client_admin.post("/api/v1/cris/converis/sync", json={
            "action": "sync", "person": {},
        })
        assert resp.status_code == 202
        assert "No author data" in resp.json().get("message", "")


class TestVIVOQueryEndpoint:
    def test_vivo_with_known_author(self, client_admin, mock_repos):
        mock_repos["author"].get_by_orcid.return_value = {"id": 7, "surname": "Garcia"}
        mock_repos["author"].get_by_scopus_id.return_value = None
        resp = client_admin.post("/api/v1/cris/vivo/query", json={
            "sparql": "SELECT ...",
            "results": [{"familyName": "Garcia", "orcid": "0000-0002-1111-2222"}],
        })
        assert resp.status_code == 202
        assert resp.json()["status"] in ("accepted", "added_to_watchlist")
        mock_repos["watchlist"].add.assert_called_once()

    def test_vivo_empty_results(self, client_admin):
        resp = client_admin.post("/api/v1/cris/vivo/query", json={
            "sparql": "SELECT ...", "results": [],
        })
        assert resp.status_code == 202
        assert "No author data" in resp.json().get("message", "")
