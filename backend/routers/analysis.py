"""
Analysis Router
Handles AI analysis endpoints
"""
from fastapi import APIRouter, HTTPException, Header, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional
from pydantic import BaseModel
from services import github_service, leetcode_service, gemini_service
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)


def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user from authorization header."""
    if not authorization:
        return None
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "")
        user = supabase.auth.get_user(token)
        return user.user
    except Exception:
        return None


class StartAnalysisRequest(BaseModel):
    user_id: str


@router.post("/start")
@limiter.limit("5/minute")
async def start_analysis(
    request: Request,
    body: StartAnalysisRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Start the AI analysis process for the user's profiles.
    1. Get user profile data from Supabase
    2. Fetch GitHub data
    3. Fetch LeetCode data  
    4. Run AI analysis
    5. Save results to database
    """
    try:
        user_id = body.user_id
        
        # Get user's profile from Supabase
        profile_response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        profile = profile_response.data[0]
        github_username = profile.get("github_username")
        leetcode_username = profile.get("leetcode_username")
        resume_text = profile.get("resume_text", "")
        
        # Fetch GitHub data
        github_data = {}
        if github_username:
            github_data = await github_service.get_full_github_data(github_username)
        
        # Fetch LeetCode data
        leetcode_data = {}
        if leetcode_username:
            leetcode_data = await leetcode_service.get_full_leetcode_data(leetcode_username)
        
        # Normalize github_data — handle both list and dict formats
        if isinstance(github_data, list):
            github_data = github_data[0] if github_data else {}
        if not isinstance(github_data, dict):
            github_data = {}
        
        # Normalize leetcode_data — handle both list and dict formats
        if isinstance(leetcode_data, list):
            leetcode_data = leetcode_data[0] if leetcode_data else {}
        if not isinstance(leetcode_data, dict):
            leetcode_data = {}
        
        # Run AI analysis
        analysis = gemini_service.analyze_profile(github_data, leetcode_data, resume_text)
        
        # Generate career paths
        career_paths = gemini_service.generate_career_paths(analysis, github_data, leetcode_data, resume_text)
        
        # Get top career path for skill gaps and roadmap
        target_career = "Full Stack Developer"  # Default
        if career_paths and isinstance(career_paths, list) and len(career_paths) > 0:
            if isinstance(career_paths[0], dict):
                target_career = career_paths[0].get("name", target_career)
        
        # Generate skill gaps
        skill_gaps = gemini_service.generate_skill_gaps(analysis, target_career, github_data, resume_text)
        
        # Generate roadmap
        roadmap = gemini_service.generate_roadmap(analysis, target_career, 6, resume_text)
        
        # Save to database
        analysis_record = {
            "user_id": user_id,
            "github_data": github_data,
            "leetcode_data": leetcode_data,
            "analysis": analysis,
            "career_paths": career_paths,
            "skill_gaps": skill_gaps,
            "roadmap": roadmap,
            "experience_level": analysis.get("experience_level", "Intermediate"),
            "strengths": analysis.get("strengths", []),
        }
        
        # Insert or update analysis
        # First check if exists
        existing = supabase.table("analyses").select("id").eq("user_id", user_id).execute()
        
        if existing.data:
            # Update existing
            supabase.table("analyses").update(analysis_record).eq("user_id", user_id).execute()
        else:
            # Insert new
            supabase.table("analyses").insert(analysis_record).execute()
        
        return {
            "status": "completed",
            "analysis": analysis,
            "career_paths": career_paths,
            "skill_gaps": skill_gaps,
            "roadmap": roadmap,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/results/{user_id}")
async def get_analysis_results(
    user_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get saved analysis results for a user.
    """
    try:
        response = supabase.table("analyses").select("*").eq("user_id", user_id).execute()
        
        if not response.data:
            return {
                "status": "no_analysis",
                "message": "No analysis found. Please run analysis first."
            }
        
        analysis = response.data[0]
        
        return {
            "status": "found",
            "analysis": analysis.get("analysis"),
            "career_paths": analysis.get("career_paths"),
            "skill_gaps": analysis.get("skill_gaps"),
            "roadmap": analysis.get("roadmap"),
            "experience_level": analysis.get("experience_level"),
            "strengths": analysis.get("strengths"),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{user_id}")
async def check_analysis_status(
    user_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Check if analysis exists for a user.
    """
    try:
        response = supabase.table("analyses").select("id, experience_level, created_at").eq("user_id", user_id).execute()
        
        if response.data:
            return {
                "status": "completed",
                "exists": True,
                "experience_level": response.data[0].get("experience_level"),
                "created_at": response.data[0].get("created_at"),
            }
        
        return {
            "status": "not_started",
            "exists": False,
        }
        
    except Exception as e:
        return {"status": "error", "exists": False}
