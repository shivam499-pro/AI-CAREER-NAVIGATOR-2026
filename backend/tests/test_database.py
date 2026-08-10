"""
Tests for core/database.py -- the backward-compatibility shim.

get_db() has no callers anywhere in the current codebase (verified by a
full-repo grep), but it's kept as a stable public entry point for any
external/future consumer. The only contract that matters is that it
delegates correctly to get_supabase() rather than diverging into its
own client instance.
"""
from core.database import get_db
from core.supabase_client import get_supabase


def test_get_db_returns_same_client_as_get_supabase(mock_supabase_singleton):
    """get_db() must return the exact same singleton instance that
    get_supabase() returns -- not a new or different client."""
    result = get_db()

    assert result is mock_supabase_singleton
    assert result is get_supabase()