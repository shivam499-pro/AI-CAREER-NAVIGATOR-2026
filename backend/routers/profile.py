"""
Profile Router
Unified profile API endpoints.

GET /api/profile/me - Get current user's profile
POST /api/profile/save - Save profile
GET /api/profile/progress - Get progress
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
from services import profile_service

# Import security middleware components
from core.middleware import (
    get_current_user,
    AuthenticatedUser,
    APIResponse,
    require_permission,
    Permission,
    format_response
)

router = APIRouter()


# Request Models
class ProfileSaveRequest(BaseModel):
    """Profile data to save."""
    # Identity
    user_type: Optional[str] = None
    # Academic
    college_name: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    current_year: Optional[str] = None
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = None
    # Professional
    current_job_title: Optional[str] = None
    current_company: Optional[str] = None
    years_of_experience: Optional[int] = None
    current_tech_stack: Optional[List[str]] = []
    reason_for_switching: Optional[str] = None
    # Common
    extra_skills: Optional[List[str]] = []
    certificates: Optional[List[str]] = []
    target_companies: Optional[List[str]] = []
    preferred_location: Optional[str] = None
    career_goal: Optional[str] = None
    open_to: Optional[str] = None
    # External
    github_username: Optional[str] = None
    leetcode_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    resume_url: Optional[str] = None
    # Ratings
    codechef_rating: Optional[int] = None
    codeforces_rating: Optional[int] = None
    hackathon_wins: Optional[int] = None


# Using centralized get_current_user from middleware


@router.get("/me")
async def get_my_profile(user: AuthenticatedUser = Depends(get_current_user)):
    """
    Get current user's profile.
    
    Returns enriched profile with merged skills and completeness score.
    """
    try:
        profile = profile_service.get_enriched_profile(user.user_id)
        return APIResponse.success_response(
            data={"profile": profile},
            message="Profile retrieved successfully"
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="PROFILE_FETCH_ERROR"
            )
        )


@router.post("/save")
async def save_my_profile(
    profile_data: ProfileSaveRequest,
    user: AuthenticatedUser = Depends(
        require_permission(Permission.WRITE_PROFILE)
    )
):
    """
    Save current user's profile.
    """
    try:
        # Convert to dict, excluding None values
        data = profile_data.dict(exclude_none=True)
        
        success = profile_service.save_profile(user.user_id, data)
        
        if success:
            return APIResponse.success_response(
                data={"saved": True},
                message="Profile saved successfully"
            )
        else:
            return JSONResponse(
                status_code=500,
                content=APIResponse.error_response(
                    "Failed to save profile",
                    code="PROFILE_SAVE_ERROR"
                )
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="PROFILE_SAVE_ERROR"
            )
        )


@router.get("/progress")
async def get_my_progress(user: AuthenticatedUser = Depends(get_current_user)):
    """
    Get user's progress through the career journey.
    
    Returns progress steps and total percentage.
    """
    try:
        progress = profile_service.get_user_progress(user.user_id)
        return APIResponse.success_response(
            data={"progress": progress}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="PROGRESS_FETCH_ERROR"
            )
        )


@router.get("/match-fit")
async def get_match_fit(user: AuthenticatedUser = Depends(get_current_user)):
    """
    Get match fit score based on user's profile and analysis.
    """
    try:
        # Get profile for career goal
        profile = profile_service.get_profile_by_user_id(user.user_id)
        target_goal = profile.get("career_goal") if profile else None
        
        # Get analysis for career paths
        from services.analysis_service import get_analysis_by_user_id
        analysis = get_analysis_by_user_id(user.user_id)
        
        if not analysis or not analysis.get("career_paths"):
            return APIResponse.success_response(
                data={
                    "score": 0,
                    "label": "Optimization Required",
                    "role": target_goal or "Unspecified",
                    "reason": "Complete analysis to see match fit"
                }
            )
        
        career_paths = analysis.get("career_paths", [])
        
        # Find best match
        match_path = None
        if target_goal:
            for path in career_paths:
                name = path.get("name") or ""
                if target_goal.lower() in name.lower():
                    match_path = path
                    break
        
        if not match_path and career_paths:
            match_path = career_paths[0]
        
        if not match_path:
            return APIResponse.success_response(
                data={
                    "score": 0,
                    "label": "No Data",
                    "role": "Pending"
                }
            )
        
        score = match_path.get("match_percentage", 0)
        label = "ELITE ALIGNMENT" if score >= 90 else "HIGHLY COMPATIBLE" if score >= 75 else "STRATEGIC MATCH" if score >= 50 else "EMERGING SYNC"
        
        return APIResponse.success_response(
            data={
                "score": score,
                "label": label,
                "role": match_path.get("name"),
                "reason": match_path.get("reason", "Based on your profile")
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="MATCH_FIT_ERROR"
            )
        )