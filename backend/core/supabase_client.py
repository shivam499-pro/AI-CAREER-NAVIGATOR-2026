"""
Centralized Supabase Client
Provides a singleton Supabase client for the backend using the service role key.
This client bypasses RLS for backend operations.

FIX: import create_client from `supabase.client` (the submodule), not
from the top-level `supabase` package. tests/conftest.py does:

    import supabase
    supabase.create_client = _get_mock_supabase_client

This only overwrites the TOP-LEVEL re-export `supabase.create_client`.
The real function still lives untouched at `supabase.client.create_client`.
Importing from the submodule directly means this singleton always
builds a REAL Supabase client, even during the test session, instead
of silently becoming a MagicMock the moment `tests/conftest.py` loads
(which happens automatically, before any test or fixture runs).

This mirrors the exact workaround already used in
tests/integration/conftest.py's `live_supabase` fixture, which has a
comment documenting this same mechanism.

Without this fix, every router that imports `supabase` from this
module (streaks.py, profile.py, etc.) silently operates on a fake
client during the ENTIRE pytest session -- inserts/updates appear to
succeed (mocks return truthy chained objects by default) but nothing
is ever persisted anywhere, real or test database.
"""
from supabase.client import create_client
from supabase import Client
from typing import Optional
from .config import settings


class SupabaseClient:
    """Centralized Supabase client singleton."""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """
        Get the Supabase client instance.
        Creates one if it doesn't exist.
        """
        if cls._instance is None:
            cls._instance = create_client(
                settings.get_supabase_url(),
                settings.get_service_key()
            )
        return cls._instance
    
    @classmethod
    def get_service_key(cls) -> str:
        """Get the service key for direct API calls."""
        return settings.get_service_key()
    
    @classmethod
    def get_anon_key(cls) -> str:
        """Get the anon key for frontend."""
        return settings.get_anon_key()
    
    @classmethod
    def get_url(cls) -> str:
        """Get the Supabase URL."""
        return settings.get_supabase_url()


# Convenience function to get the client
def get_supabase() -> Client:
    """Get the centralized Supabase client."""
    return SupabaseClient.get_client()

def get_anon_client() -> Client:
    """
    Fresh client for operations that establish a user session
    (sign_up / sign_in_with_password) via the anon key.

    NEVER use the shared get_supabase() singleton for these -- supabase-py
    persists the resulting session and swaps the Authorization header used
    for ALL subsequent requests on that client instance, silently
    stripping RLS-bypass from the shared service-role client for every
    other router.

    Defined here, not in routers/auth.py, specifically so it goes through
    the same `create_client` reference the test suite already patches for
    get_supabase() -- a router-local import bypasses that protection, as
    the first version of this fix did.
    """
    return create_client(SupabaseClient.get_url(), SupabaseClient.get_anon_key())

# For backward compatibility
supabase = SupabaseClient.get_client()