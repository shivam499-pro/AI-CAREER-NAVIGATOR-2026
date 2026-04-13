from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from services import career_brain_service

router = APIRouter()


@router.get("/career-brain")
async def get_career_brain(authorization: Optional[str] = Header(None)):
    """
    Get AI Career Brain - comprehensive career intelligence.
    
    Returns:
    - Job readiness score (0-100)
    - Skill analysis (strong, weak, missing)
    - Behavioral insights
    - Actionable recommendations
    - Risk alerts
    - Progress summary
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get user from token
    import httpx
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    token = authorization.replace("Bearer ", "")
    
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            f"{supabase_url}/auth/v1/user",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {token}"}
        )
        
        if user_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_info = user_resp.json()
        user_id = user_info.get("id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not found")
    
    # Get career brain data
    try:
        result = await career_brain_service.get_career_brain(user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))