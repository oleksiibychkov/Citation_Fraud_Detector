"""Supabase client initialization."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client

from cfd.config.settings import Settings

_client: Client | None = None
_lock = threading.Lock()


def get_supabase_client(settings: Settings | None = None) -> Client:
    """Get or create Supabase client singleton."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                from supabase import create_client

                s = settings or Settings()
                _client = create_client(s.supabase_url, s.supabase_key)
    return _client


def reset_client() -> None:
    """Reset the cached client (for testing)."""
    global _client
    _client = None
