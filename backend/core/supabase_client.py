"""
Centralized Supabase Client
Provides a singleton Supabase client for the backend using the service role key.
This client bypasses RLS for backend operations.
"""
from supabase import create_client, Client
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


# For backward compatibility
supabase = SupabaseClient.get_client()