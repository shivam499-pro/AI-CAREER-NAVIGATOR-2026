"""
core/database.py
Backward-compatibility shim — all new code should import get_supabase()
from core.supabase_client directly.
"""
from core.supabase_client import get_supabase


def get_db():
    """Get the centralized Supabase client. Use this instead of bare `supabase`."""
    return get_supabase()