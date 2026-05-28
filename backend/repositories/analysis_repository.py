"""
Analysis Repository - Phase 1 Step 2 (DIP Fix)
Abstracts all database operations for analyses.
Swap Supabase for any other DB by adding a new implementation.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime


class AnalysisRepository(ABC):
    """Abstract repository — depend on this, not on Supabase directly."""

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch analysis row for a user. Returns None if not found."""
        ...

    @abstractmethod
    def upsert(self, data: Dict[str, Any]) -> bool:
        """Insert or update an analysis row. Returns True on success."""
        ...


class SupabaseAnalysisRepository(AnalysisRepository):
    """Concrete Supabase implementation of AnalysisRepository."""

    def __init__(self):
        from core.supabase_client import get_supabase
        self._get_supabase = get_supabase

    def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            supabase = self._get_supabase()
            response = (
                supabase.table("analyses")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"[SupabaseAnalysisRepository] get_by_user_id error: {e}")
            return None

    def upsert(self, data: Dict[str, Any]) -> bool:
        try:
            supabase = self._get_supabase()
            response = (
                supabase.table("analyses")
                .upsert(data, on_conflict="user_id")
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            print(f"[SupabaseAnalysisRepository] upsert error: {e}")
            return False