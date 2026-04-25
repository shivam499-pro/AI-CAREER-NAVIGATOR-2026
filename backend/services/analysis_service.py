"""
Analysis Service
Business logic for analysis operations including:
- Generate AI insights
- Career recommendations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from core.supabase_client import get_supabase
from services.profile_service import get_enriched_profile
from services.job_matching_service import match_jobs
from services import github_service
from services import leetcode_service
from services import gemini_service


def get_analysis_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get analysis for a user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        Analysis data or None
    """
    try:
        supabase = get_supabase()
        response = supabase.table("analyses").select("*").eq("user_id", user_id).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching analysis: {e}")
        return None


def save_analysis(user_id: str, analysis_data: Dict[str, Any]) -> bool:
    """
    Save analysis results.
    
    Args:
        user_id: The user's unique identifier
        analysis_data: Analysis data to save
        
    Returns:
        True if successful
    """
    try:
        supabase = get_supabase()
        
        data = {
            "user_id": user_id,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Add analysis fields to full analysis object
        analysis_obj = {}
        if "strengths" in analysis_data:
            analysis_obj["strengths"] = analysis_data["strengths"]
            data["strengths"] = analysis_data["strengths"]
        if "weaknesses" in analysis_data:
            analysis_obj["weaknesses"] = analysis_data["weaknesses"]
            data["weaknesses"] = analysis_data["weaknesses"]
        if "experience_level" in analysis_data:
            analysis_obj["experience_level"] = analysis_data["experience_level"]
            data["experience_level"] = analysis_data["experience_level"]
        if "career_paths" in analysis_data:
            data["career_paths"] = analysis_data["career_paths"]
        if "skill_gap" in analysis_data:
            analysis_obj["skill_gap"] = analysis_data["skill_gap"]
            data["skill_gap"] = analysis_data["skill_gap"]
        
        # Save full analysis object to 'analysis' column
        if analysis_obj:
            data["analysis"] = analysis_obj
        
        # Always use upsert to prevent duplicate rows
        response = supabase.table("analyses").upsert(data, on_conflict="user_id").execute()
        
        return bool(response.data)
    except Exception as e:
        print(f"Error saving analysis: {e}")
        return False


async def run_analysis(user_id: str) -> Dict[str, Any]:
    """
    Run AI analysis for a user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        Analysis results
    """
    try:
        # Get enriched profile
        profile = get_enriched_profile(user_id)
        
        if not profile.get("exists"):
            return {
                "success": False,
                "error": "Profile not found. Please complete your profile first."
            }
        
        # Get profile data
        profile_data = profile.get("data", {})
        print("PROFILE DATA:", profile_data)
        
        # Extract usernames
        github_username = profile_data.get("github_username", "")
        leetcode_username = profile_data.get("leetcode_username", "")
        print("GITHUB USERNAME:", github_username)
        print("LEETCODE USERNAME:", leetcode_username)


        # Fetch GitHub data (pass empty dict if username missing)
        if github_username:
            github_data = await github_service.get_full_github_data(github_username)
        else:
            github_data = {}
        
        # Fetch LeetCode data (pass empty dict if username missing)
        if leetcode_username:
            leetcode_data = await leetcode_service.get_full_leetcode_data(leetcode_username)
        else:
            leetcode_data = {}
        
        print("GITHUB DATA:", github_data)
        print("LEETCODE DATA:", leetcode_data)
        
        # Get resume text
        resume_text = profile_data.get("resume_text", "")
        
        # Call Gemini for combined analysis
        result = gemini_service.run_combined_analysis(
            github_data,
            leetcode_data,
            resume_text,
            profile_data
        )
        print("GEMINI RESULT:", result)
        
        # Check if Gemini returned success: False
        if result.get("success") == False:
            error_msg = result.get("error", "Unknown error from Gemini")
            print(f"Gemini analysis failed: {error_msg}")
            raise Exception(error_msg)
        
        # Extract data from result
        analysis_result = result.get("data", {})
        
        # Save to Supabase with upsert
        supabase = get_supabase()
        
        save_data = {
            "user_id": user_id,
            "github_data": github_data,
            "leetcode_data": leetcode_data,
            "analysis": analysis_result,
            "career_paths": analysis_result.get("career_paths", []),
            "skill_gaps": analysis_result.get("skill_gaps", []),
            "roadmap": analysis_result.get("roadmap", {}),
            "experience_level": analysis_result.get("analysis", {}).get("experience_level", "Intermediate"),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Use upsert to prevent duplicate rows
        response = supabase.table("analyses").upsert(save_data, on_conflict="user_id").execute()
        
        return {
            "success": True,
            "analysis": analysis_result
        }
    except Exception as e:
        print(f"Error running analysis: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_career_recommendations(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get career path recommendations.
    
    Args:
        user_id: The user's unique identifier
        limit: Number of recommendations
        
    Returns:
        List of career recommendations
    """
    try:
        analysis = get_analysis_by_user_id(user_id)
        
        if not analysis or not analysis.get("career_paths"):
            return []
        
        paths = analysis.get("career_paths", [])
        return paths[:limit]
    except Exception as e:
        print(f"Error getting career recommendations: {e}")
        return []


def get_skill_gaps(user_id: str) -> List[Dict[str, Any]]:
    """
    Get skill gaps for a user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        List of skill gaps with priorities
    """
    try:
        analysis = get_analysis_by_user_id(user_id)
        
        if not analysis:
            return []
        
        return analysis.get("skill_gap", [])
    except Exception as e:
        print(f"Error getting skill gaps: {e}")
        return []
