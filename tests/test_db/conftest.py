"""Shared fixtures for DB repository tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_client():
    """Mock Supabase client with chainable table operations."""
    client = MagicMock()
    table = MagicMock()
    for method in (
        "select", "insert", "upsert", "update", "delete",
        "eq", "lt", "gte", "lte", "order", "limit", "range",
    ):
        getattr(table, method).return_value = table
    execute_result = MagicMock()
    execute_result.data = []
    execute_result.count = 0
    table.execute.return_value = execute_result
    client.table.return_value = table
    return client


def set_execute_data(client, data, count=None):
    """Configure the mock chain's execute() to return specific data."""
    result = client.table.return_value.execute.return_value
    result.data = data
    result.count = count if count is not None else len(data)
