"""
Enhanced Profile Router
Handles enhanced profile data (academic, skills, experience, achievements, goals)
"""
from fastapi import APIRouter, HTTPException, Depends
from lib.auth import get_current_user
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


@router.get("/enhanced")
async def get_enhanced_profile(user: Any = Depends(get_current_user)):
    """
    Get enhanced profile data for the current authenticated user.
    """
    try:
        user_id = user.id
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


@router.post("/enhanced")
async def save_enhanced_profile(profile: EnhancedProfile, user: Any = Depends(get_current_user)):
    """
    Save enhanced profile data for the current authenticated user.
    """
    try:
        user_id = user.id
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

@router.get("/progress")
async def get_user_progress(user: Any = Depends(get_current_user)):
    """
    Calculate and return the live progress of the user's career journey.
    Phases:
    1. Identity Setup (25%) - Profile exists
    2. Intelligence Sync (25%) - GitHub/LeetCode linked
    3. Strategic Analysis (25%) - Analysis completed
    4. Readiness Simulation (25%) - Interview sessions recorded
    """
    try:
        user_id = user.id
        
        # 1. Identity Phase
        profile_res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        profile = profile_res.data[0] if profile_res.data else None
        
        # 2. Sync Phase
        is_synced = False
        if profile:
            is_synced = bool(profile.get("github_username") or profile.get("leetcode_username"))
        
        # 3. Analysis Phase
        # Changed to results table since analyses was showing as empty for some users 
        analysis_res = supabase.table("analyses").select("id").eq("user_id", user_id).execute()
        has_analysis = len(analysis_res.data) > 0
        
        # 4. Simulation Phase
        interview_res = supabase.table("interviews").select("id").eq("user_id", user_id).execute()
        has_interview = len(interview_res.data) > 0
        
        steps = [
            {"id": "id", "label": "Identity Established", "desc": "Account Initialized", "status": "complete" if profile else "pending", "value": 25 if profile else 0},
            {"id": "sync", "label": "Intelligence Synced", "desc": "External Nodes Connected", "status": "complete" if is_synced else "pending", "value": 25 if is_synced else 0},
            {"id": "analysis", "label": "Analysis Ready", "desc": "AI Strategic Analysis complete", "status": "complete" if has_analysis else "pending", "value": 25 if has_analysis else 0},
            {"id": "simulation", "label": "Boardroom Simulation", "desc": "Live Practice Interview Recorded", "status": "complete" if has_interview else "pending", "value": 25 if has_interview else 0},
        ]
        
        total_progress = sum(s["value"] for s in steps)
        
        return {
            "total": total_progress,
            "steps": steps,
            "status": "ELITE" if total_progress == 100 else "EXECUTIVE" if total_progress >= 50 else "INITIALIZED"
        }
    except Exception as e:
        return {"error": str(e), "total": 0, "steps": []}

@router.get("/match-fit")
async def get_match_fit(user: Any = Depends(get_current_user)):
    """
    Retrieve real-time match fit score based on the user's latest AI analysis.
    """
    try:
        user_id = user.id
        
        # Get target career goal from profile
        profile_res = supabase.table("profiles").select("career_goal").eq("user_id", user_id).execute()
        target_goal = profile_res.data[0].get("career_goal") if profile_res.data else None
        
        # Get analysis results
        analysis_res = supabase.table("analyses").select("career_paths").eq("user_id", user_id).execute()
        
        if not analysis_res.data:
            return {
                "score": 0,
                "label": "Optimization Required",
                "role": target_goal or "Unspecified Node",
                "reason": "Initial analysis not yet completed within the Antigravity Hub."
            }
            
        career_paths = analysis_res.data[0].get("career_paths", [])
        
        # Find best match or match for the target goal
        match_path = None
        if target_goal:
            for path in career_paths:
                name = path.get("name") or path.get("career_name") or ""
                if target_goal.lower() in name.lower():
                    match_path = path
                    break
        
        if not match_path and career_paths:
            match_path = career_paths[0] # Default to best match
            
        if not match_path:
            return {"score": 0, "label": "No Data", "role": "Pending"}

        score = match_path.get("match_percentage", 0)
        label = "ELITE ALIGNMENT" if score >= 90 else "HIGHLY COMPATIBLE" if score >= 75 else "STRATEGIC MATCH" if score >= 50 else "EMERGING SYNC"
            
        return {
            "score": score,
            "label": label,
            "role": match_path.get("name") or match_path.get("career_name"),
            "reason": match_path.get("reason", "Strategic alignment confirmed via AI Core.")
        }
    except Exception as e:
        return {"error": str(e), "score": 0}
