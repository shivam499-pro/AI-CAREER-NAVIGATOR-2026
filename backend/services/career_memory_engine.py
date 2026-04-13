"""
Career Memory Engine
Tracks user evolution over time for career paths.
Non-critical feature - failures must not break API.
"""
from supabase import create_client
from typing import Optional, Dict, Any
import os
import logging
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Structured log prefix
MEMORY_LOG_PREFIX = "[MEMORY_ENGINE]"

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

# Lazy initialization - client created on first use
_supabase_client = None


def _get_supabase():
    """Get or create Supabase client lazily."""
    global _supabase_client
    if _supabase_client is None:
        if supabase_url and supabase_key:
            _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client


def _calculate_trend(scores: list) -> str:
    """
    Calculate trend based on the last 3 session scores.
    
    Rules:
    - increasing scores → improving
    - stable (±5%) → stable
    - decreasing → declining
    """
    if not scores or len(scores) < 2:
        return "stable"
    
    # Get last up to 3 scores (most recent)
    recent_scores = scores[-3:] if len(scores) >= 3 else scores
    
    if len(recent_scores) < 2:
        return "stable"
    
    # Calculate difference between first and last score
    first_score = recent_scores[0]
    last_score = recent_scores[-1]
    
    # If only 2 scores, compare directly
    if len(recent_scores) == 2:
        if last_score > first_score:
            return "improving"
        elif last_score < first_score:
            return "declining"
        else:
            return "stable"
    
    # For 3+ scores, check overall trend
    # Count increases and decreases
    increases = 0
    decreases = 0
    
    for i in range(1, len(recent_scores)):
        if recent_scores[i] > recent_scores[i-1]:
            increases += 1
        elif recent_scores[i] < recent_scores[i-1]:
            decreases += 1
    
    # Determine trend based on majority
    if increases > decreases:
        return "improving"
    elif decreases > increases:
        return "declining"
    else:
        # Check if stable (±5%)
        if first_score > 0:
            change_percent = abs(last_score - first_score) / first_score
            if change_percent <= 0.05:
                return "stable"
        return "stable"


def _calculate_confidence(score_variance: float, session_count: int) -> float:
    """
    Calculate confidence score based on performance consistency.
    
    - Higher session count → higher confidence
    - Lower variance → higher confidence
    - Returns float between 0 and 1
    """
    if session_count == 1:
        return 0.5
    
    # Base confidence from session count (caps at 0.3 for 10+ sessions)
    session_factor = min(0.3, session_count * 0.03)
    
    # Consistency factor based on variance
    # Lower variance = higher consistency
    if score_variance == 0:
        consistency_factor = 0.7
    else:
        # Variance typically 0-100 for scores
        # Higher variance = lower consistency
        consistency_factor = max(0.0, 0.7 - (score_variance / 200))
    
    confidence = min(1.0, session_factor + consistency_factor)
    return round(confidence, 2)


def update_user_memory(user_id: str, session_data: Dict[str, Any]) -> bool:
    """
    Update user career memory based on interview session.
    
    This function is non-critical - failures should not break the API.
    
    Args:
        user_id: UUID of the user
        session_data: Dictionary containing:
            - career_path: str (required)
            - score: int/float (required) - interview score
            - feedback: str (optional) - interview feedback
            - timestamp: datetime (optional)
    
    Returns:
        bool: True if successful, False otherwise
    
    Logic:
    - If record exists for (user_id + career_path):
        - Update average performance_score
        - Increment session_count
        - Update confidence_score based on consistency
        - Update trend (improving/stable/declining)
    - Else:
        - Create new memory record
    """
    try:
        supabase = _get_supabase()
        if not supabase:
            logger.warning(f"{MEMORY_LOG_PREFIX} Supabase not initialized")
            return False
        
        # Extract session data
        career_path = session_data.get("career_path")
        score = session_data.get("score", 0)
        
        if not career_path:
            logger.warning(f"{MEMORY_LOG_PREFIX} Missing career_path in session data")
            return False
        
        # Try to find existing record
        existing_response = supabase.table("user_career_memory").select(
            "id, performance_score, session_count, confidence_score, trend, created_at"
        ).eq("user_id", user_id).eq("career_path", career_path).execute()
        
        if existing_response.data and len(existing_response.data) > 0:
            # Update existing record
            existing = existing_response.data[0]
            existing_id = existing["id"]
            
            # Get current session count
            old_session_count = existing.get("session_count", 1)
            old_score = existing.get("performance_score", score)
            
            # Calculate new average performance score
            new_session_count = old_session_count + 1
            new_avg_score = int(((old_score * old_session_count) + score) / new_session_count)
            
            # Fetch recent scores for trend calculation
            # Get up to last 3 sessions for this career path
            recent_response = supabase.table("interview_sessions").select(
                "total_score, created_at"
            ).eq("user_id", user_id).eq("career_path", career_path).order(
                "created_at", desc=True
            ).limit(3).execute()
            
            recent_scores = [r["total_score"] for r in recent_response.data] if recent_response.data else []
            recent_scores.append(score)  # Add current score
            
            # Calculate trend
            new_trend = _calculate_trend(recent_scores)
            
            # Calculate variance for confidence
            if len(recent_scores) > 1:
                import statistics
                try:
                    score_variance = statistics.stdev(recent_scores) if len(recent_scores) > 1 else 0
                except statistics.StatisticsError:
                    score_variance = 0
            else:
                score_variance = 0
            
            # Calculate new confidence score
            new_confidence = _calculate_confidence(score_variance, new_session_count)
            
            # Update the record
            update_response = supabase.table("user_career_memory").update({
                "performance_score": new_avg_score,
                "session_count": new_session_count,
                "confidence_score": new_confidence,
                "trend": new_trend,
                "last_updated": datetime.utcnow().isoformat()
            }).eq("id", existing_id).execute()
            
            logger.info(
                f"{MEMORY_LOG_PREFIX} Updated memory for user={user_id} "
                f"career_path={career_path} sessions={new_session_count} "
                f"trend={new_trend}"
            )
            
        else:
            # Create new memory record
            new_record = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "career_path": career_path,
                "skill_area": session_data.get("skill_area", career_path),
                "performance_score": int(score),
                "confidence_score": 0.5,
                "trend": "stable",
                "session_count": 1,
                "last_updated": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            insert_response = supabase.table("user_career_memory").insert(new_record).execute()
            
            logger.info(
                f"{MEMORY_LOG_PREFIX} Created memory for user={user_id} "
                f"career_path={career_path}"
            )
        
        return True
        
    except Exception as e:
        # Log error silently - non-critical feature
        logger.error(f"{MEMORY_LOG_PREFIX} Error updating memory: {str(e)}")
        return False


def get_user_memory(user_id: str, career_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get user career memory data.
    
    Args:
        user_id: UUID of the user
        career_path: Optional career path to filter by
    
    Returns:
        Dictionary with memory data or None if not found/error
    """
    try:
        supabase = _get_supabase()
        if not supabase:
            return None
        
        query = supabase.table("user_career_memory").select("*").eq("user_id", user_id)
        
        if career_path:
            query = query.eq("career_path", career_path)
        
        response = query.execute()
        
        if response.data:
            return response.data
        
        return None
        
    except Exception as e:
        logger.error(f"{MEMORY_LOG_PREFIX} Error getting memory: {str(e)}")
        return None