"""
Career Evolution Engine
Predictive intelligence system that detects long-term skill evolution patterns.
Provides structured data for AI recommendations.
"""
from supabase import create_client
from typing import Optional, Dict, Any, List
import os
import logging
import time
import uuid
from datetime import datetime
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Structured log prefix
EVOLUTION_LOG_PREFIX = "[EVOLUTION_ENGINE]"

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

# Lazy initialization - client created on first use
_supabase_client = None

# In-memory cache for evolution profiles
# Key: user_id -> (timestamp, data)
_evolution_cache: Dict[str, tuple] = {}
EVOLUTION_CACHE_TTL = 900  # 15 minutes


def _get_supabase():
    """Get or create Supabase client lazily."""
    global _supabase_client
    if _supabase_client is None:
        if supabase_url and supabase_key:
            _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client


def _get_cached_evolution(user_id: str) -> Optional[Dict[str, Any]]:
    """Get cached evolution profile if valid."""
    global _evolution_cache
    
    if user_id in _evolution_cache:
        timestamp, data = _evolution_cache[user_id]
        current_time = time.time()
        if current_time - timestamp <= EVOLUTION_CACHE_TTL:
            return data
        else:
            # Expired - remove it
            del _evolution_cache[user_id]
    
    return None


def _set_cached_evolution(user_id: str, data: Dict[str, Any]) -> None:
    """Store evolution profile in cache with current timestamp."""
    global _evolution_cache
    _evolution_cache[user_id] = (time.time(), data)


def _calculate_volatility(scores: List[float]) -> float:
    """
    Calculate volatility = standard_deviation(scores) / mean(scores)
    Clamped between 0-1.
    
    Interpretation:
    0.0-0.2 → stable learner
    0.2-0.5 → moderate fluctuation
    0.5+ → inconsistent performance
    """
    if not scores or len(scores) < 2:
        return 0.0
    
    try:
        mean_score = statistics.mean(scores)
        if mean_score == 0:
            return 0.0
        
        stdev = statistics.stdev(scores)
        volatility = stdev / mean_score
        
        # Clamp between 0 and 1
        return round(min(1.0, max(0.0, volatility)), 2)
    except statistics.StatisticsError:
        return 0.0


def _determine_growth_state(career_paths: List[Dict[str, Any]]) -> str:
    """
    Determine overall growth state based on career paths.
    
    Rules:
    - If majority career paths = improving → "growing"
    - If mixed → "stagnating"
    - If majority declining → "declining"
    """
    if not career_paths:
        return "stagnating"
    
    improving_count = 0
    declining_count = 0
    stable_count = 0
    
    for path in career_paths:
        trend = path.get("trend", "stable")
        if trend == "improving":
            improving_count += 1
        elif trend == "declining":
            declining_count += 1
        else:
            stable_count += 1
    
    total = len(career_paths)
    
    # Majority rule
    if improving_count > total / 2:
        return "growing"
    elif declining_count > total / 2:
        return "declining"
    else:
        return "stagnating"


def get_user_evolution_profile(user_id: str) -> Dict[str, Any]:
    """
    Get user evolution profile with skill aggregation.
    
    Returns:
    {
      "user_id": "...",
      "career_paths": [
        {
          "career_path": "AI/ML Engineer",
          "avg_score": 72,
          "trend": "improving",
          "volatility": 0.12,
          "total_sessions": 8,
          "confidence": 0.81
        }
      ],
      "overall_growth_state": "growing | stagnating | declining"
    }
    """
    try:
        # Check cache first
        cached = _get_cached_evolution(user_id)
        if cached:
            logger.info(f"{EVOLUTION_LOG_PREFIX} Cache hit for user={user_id}")
            return cached
        
        supabase = _get_supabase()
        if not supabase:
            logger.warning(f"{EVOLUTION_LOG_PREFIX} Supabase not initialized")
            return _get_fallback_profile(user_id)
        
        # Fetch career memory data for all career paths
        memory_response = supabase.table("user_career_memory").select(
            "career_path, performance_score, session_count, confidence_score, trend"
        ).eq("user_id", user_id).execute()
        
        career_paths_data = memory_response.data if memory_response.data else []
        
        # Also fetch interview sessions for volatility calculation
        sessions_response = supabase.table("interview_sessions").select(
            "career_path, total_score"
        ).eq("user_id", user_id).execute()
        
        sessions_data = sessions_response.data if sessions_response.data else []
        
        # Group sessions by career path for volatility calculation
        sessions_by_path: Dict[str, List[float]] = {}
        for session in sessions_data:
            path = session.get("career_path")
            if path:
                if path not in sessions_by_path:
                    sessions_by_path[path] = []
                sessions_by_path[path].append(float(session.get("total_score", 0)))
        
        # Build career paths list
        career_paths = []
        
        for memory in career_paths_data:
            career_path = memory.get("career_path")
            
            # Get scores for this career path for volatility
            path_scores = sessions_by_path.get(career_path, [])
            
            # Calculate volatility
            volatility = _calculate_volatility(path_scores)
            
            # Get avg score from memory
            avg_score = memory.get("performance_score", 0)
            
            career_paths.append({
                "career_path": career_path,
                "avg_score": avg_score,
                "trend": memory.get("trend", "stable"),
                "volatility": volatility,
                "total_sessions": memory.get("session_count", 1),
                "confidence": memory.get("confidence_score", 0.5)
            })
        
        # Determine overall growth state
        overall_growth_state = _determine_growth_state(career_paths)
        
        # Build result
        result = {
            "user_id": user_id,
            "career_paths": career_paths,
            "overall_growth_state": overall_growth_state
        }
        
        # Cache the result
        _set_cached_evolution(user_id, result)
        
        logger.info(
            f"{EVOLUTION_LOG_PREFIX} Generated profile for user={user_id} "
            f"paths={len(career_paths)} state={overall_growth_state}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"{EVOLUTION_LOG_PREFIX} Error generating profile: {str(e)}")
        return _get_fallback_profile(user_id)


def _get_fallback_profile(user_id: str) -> Dict[str, Any]:
    """Return safe fallback when no data exists."""
    return {
        "user_id": user_id,
        "career_paths": [],
        "overall_growth_state": "stagnating"
    }


def update_user_evolution_profile(user_id: str) -> bool:
    """
    Update user evolution profile after session.
    
    This invalidates the cache to force recomputation on next read.
    Non-critical - failures should not break API.
    """
    try:
        # Invalidate cache by removing entry
        global _evolution_cache
        if user_id in _evolution_cache:
            del _evolution_cache[user_id]
        
        logger.info(f"{EVOLUTION_LOG_PREFIX} Invalidated cache for user={user_id}")
        return True
        
    except Exception as e:
        logger.error(f"{EVOLUTION_LOG_PREFIX} Error updating profile: {str(e)}")
        return False


def clear_cache(user_id: Optional[str] = None) -> None:
    """
    Clear evolution cache.
    
    Args:
        user_id: If provided, clear only this user's cache.
               If None, clear all caches.
    """
    global _evolution_cache
    
    if user_id:
        if user_id in _evolution_cache:
            del _evolution_cache[user_id]
    else:
        _evolution_cache.clear()