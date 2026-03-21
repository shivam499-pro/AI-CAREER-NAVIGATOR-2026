"""
Enhanced Profile Router
Handles enhanced profile data (academic, skills, experience, achievements, goals)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)


class EnhancedProfile(BaseModel):
    college_name: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    current_year: Optional[str] = None
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = None
    extra_skills: Optional[List[str]] = []
    experience: Optional[List[dict]] = []
    certificates: Optional[List[dict]] = []
    target_companies: Optional[List[str]] = []
    preferred_location: Optional[str] = None
    career_goal: Optional[str] = None
    open_to: Optional[str] = None
    codechef_rating: Optional[int] = None
    codeforces_rating: Optional[int] = None
    hackathon_wins: Optional[int] = None


@router.get("/enhanced/{user_id}")
async def get_enhanced_profile(user_id: str):
    """
    Get enhanced profile data for a user.
    """
    try:
        response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        if not response.data:
            return {"error": "Profile not found"}
        
        profile = response.data[0]
        
        return {
            "college_name": profile.get("college_name"),
            "degree": profile.get("degree"),
            "branch": profile.get("branch"),
            "current_year": profile.get("current_year"),
            "graduation_year": profile.get("graduation_year"),
            "cgpa": profile.get("cgpa"),
            "extra_skills": profile.get("extra_skills", []),
            "experience": profile.get("experience", []),
            "certificates": profile.get("certificates", []),
            "target_companies": profile.get("target_companies", []),
            "preferred_location": profile.get("preferred_location"),
            "career_goal": profile.get("career_goal"),
            "open_to": profile.get("open_to"),
            "codechef_rating": profile.get("codechef_rating"),
            "codeforces_rating": profile.get("codeforces_rating"),
            "hackathon_wins": profile.get("hackathon_wins"),
        }
        
    except Exception as e:
        return {"error": str(e)}


@router.post("/enhanced/{user_id}")
async def save_enhanced_profile(user_id: str, profile: EnhancedProfile):
    """
    Save enhanced profile data for a user.
    """
    try:
        profile_data = profile.dict(exclude_unset=True)
        
        # Update profile in Supabase
        response = supabase.table("profiles").update(profile_data).eq("user_id", user_id).execute()
        
        if not response.data:
            # Profile doesn't exist, create it
            response = supabase.table("profiles").insert({
                "user_id": user_id,
                **profile_data
            }).execute()
        
        return {"success": True, "message": "Profile saved successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
