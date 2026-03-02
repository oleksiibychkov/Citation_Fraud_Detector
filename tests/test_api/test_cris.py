"""Tests for CRIS integration stubs."""

from __future__ import annotations


class TestCrisStubs:
    def test_pure_webhook(self, client_admin):
        resp = client_admin.post("/api/v1/cris/pure/webhook", json={"event": "new_researcher"})
        assert resp.status_code == 202
        assert resp.json()["status"] == "accepted"

    def test_converis_sync(self, client_admin):
        resp = client_admin.post("/api/v1/cris/converis/sync", json={"action": "sync"})
        assert resp.status_code == 202
        assert resp.json()["status"] == "accepted"

    def test_vivo_query(self, client_admin):
        resp = client_admin.post("/api/v1/cris/vivo/query", json={"sparql": "SELECT ..."})
        assert resp.status_code == 202
        assert resp.json()["status"] == "accepted"
