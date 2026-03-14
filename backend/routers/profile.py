from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from services import github_service, leetcode_service, resume_service
from models.user import UserProfile

router = APIRouter()

class ProfileInput(BaseModel):
    github_url: Optional[str] = None
    leetcode_username: Optional[str] = None
    linkedin_url: Optional[str] = None

@router.post("/")
async def submit_profile(
    profile_data: ProfileInput,
    authorization: Optional[str] = Header(None)
):
    """
    Submit user profile URLs for analysis.
    """
    try:
        # In production, get user_id from auth token
        user_id = "temp_user_id"  # TODO: Extract from auth token
        
        result = {
            "user_id": user_id,
            "github_url": profile_data.github_url,
            "leetcode_username": profile_data.leetcode_username,
            "linkedin_url": profile_data.linkedin_url,
            "status": "received"
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_profile(
    authorization: Optional[str] = Header(None)
):
    """
    Get user's current profile data.
    """
    try:
        # In production, get user_id from auth token
        user_id = "temp_user_id"
        
        return {
            "user_id": user_id,
            "github_url": None,
            "leetcode_username": None,
            "linkedin_url": None,
            "resume_url": None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume/upload")
async def upload_resume(
    file_path: str,
    authorization: Optional[str] = Header(None)
):
    """
    Upload and parse resume PDF.
    """
    try:
        # In production, extract text from uploaded PDF
        resume_text = resume_service.extract_text(file_path)
        
        return {
            "status": "uploaded",
            "text_length": len(resume_text)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
