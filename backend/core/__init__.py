"""
Core Module
Provides centralized configuration and Supabase client for the backend.
"""
from .config import settings, Settings
from .supabase_client import SupabaseClient, get_supabase, supabase

__all__ = [
    "settings",
    "Settings", 
    "SupabaseClient",
    "get_supabase",
    "supabase"
]