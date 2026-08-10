"""
Tests for core/supabase_client.py's SupabaseClient accessor classmethods.

get_service_key(), get_anon_key(), and get_url() aren't called anywhere
in the current codebase (verified by grep), but they're public
classmethods on a shared singleton -- worth pinning down that each one
delegates to the correct underlying settings accessor, not a copy-pasted
wrong one (an easy mistake with three near-identical one-liners sitting
next to each other).
"""
from unittest.mock import patch
from core.supabase_client import SupabaseClient, get_supabase


def test_get_supabase_returns_singleton_client(mock_supabase_singleton):
    """get_supabase() -- the module-level convenience function -- must
    return the actual singleton client, not None or a fresh instance.
    Written directly rather than relying on other test files' incidental
    calls to this function to cover it."""
    result = get_supabase()

    assert result is mock_supabase_singleton
    assert result is SupabaseClient.get_client()


def test_get_service_key_delegates_to_settings():
    with patch("core.supabase_client.settings") as mock_settings:
        mock_settings.get_service_key.return_value = "service-key-123"

        result = SupabaseClient.get_service_key()

        assert result == "service-key-123"
        mock_settings.get_service_key.assert_called_once()


def test_get_anon_key_delegates_to_settings():
    with patch("core.supabase_client.settings") as mock_settings:
        mock_settings.get_anon_key.return_value = "anon-key-456"

        result = SupabaseClient.get_anon_key()

        assert result == "anon-key-456"
        mock_settings.get_anon_key.assert_called_once()


def test_get_url_delegates_to_settings():
    with patch("core.supabase_client.settings") as mock_settings:
        mock_settings.get_supabase_url.return_value = "https://example.supabase.co"

        result = SupabaseClient.get_url()

        assert result == "https://example.supabase.co"
        mock_settings.get_supabase_url.assert_called_once()