"""
Career Router
Handles career evolution and intelligence endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from supabase import create_client
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")


def get_current_user(authorization: str = Header(None)) -> str:
    """
    Dependency to extract and verify the JWT token from Authorization header.
    Returns the user_id from the token.
    Raises HTTPException 401 if token is missing or invalid.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Server configuration error")
        
        supabase = create_client(supabase_url, supabase_key)
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_response.user.id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/evolution/{user_id}")
async def get_career_evolution(
    user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Get user career evolution profile.
    
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
    
    Features:
    - 15-minute in-memory cache
    - Safe fallback if no data exists
    """
    # Verify the user_id from the token matches the requested user_id
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        from services import career_evolution_engine
        
        # Get evolution profile (cached automatically)
        profile = career_evolution_engine.get_user_evolution_profile(user_id)
        
        logger.info(
            f"[Career] Evolution profile for user={user_id} "
            f"state={profile.get('overall_growth_state')}"
        )
        
        return profile
        
    except Exception as e:
        logger.error(f"[Career] Error getting evolution profile: {str(e)}")
        # Return fallback profile on error
        return {
            "user_id": user_id,
            "career_paths": [],
            "overall_growth_state": "stagnating"
        }