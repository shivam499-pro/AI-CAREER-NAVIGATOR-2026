from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from services import gemini_service
import uuid

router = APIRouter()

@router.post("/start")
async def start_analysis(
    authorization: Optional[str] = Header(None)
):
    """
    Start the AI analysis process for the user's profiles.
    """
    try:
        # Generate analysis ID
        analysis_id = str(uuid.uuid4())
        
        # In production, this would trigger the full analysis pipeline
        # For now, return the analysis ID
        
        return {
            "analysis_id": analysis_id,
            "status": "started",
            "message": "Analysis started. Use the analysis_id to check status."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get the results of an analysis.
    """
    try:
        # In production, fetch from database
        # For now, return mock data
        
        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "strengths": [
                "Strong JavaScript/TypeScript skills",
                "Good project portfolio",
                "Active GitHub contributions"
            ],
            "weaknesses": [
                "Limited cloud experience",
                "No DevOps certifications"
            ],
            "experience_level": "Intermediate",
            "career_paths": [
                {
                    "name": "Full Stack Developer",
                    "match_percentage": 85,
                    "reason": "Strong frontend skills with growing backend experience"
                },
                {
                    "name": "Data Scientist",
                    "match_percentage": 60,
                    "reason": "Good analytical skills, needs more Python/Math background"
                }
            ],
            "skill_gap": [
                {"skill": "AWS", "have": False, "priority": 1, "resources": []},
                {"skill": "Docker", "have": True, "priority": 2, "resources": []},
                {"skill": "PostgreSQL", "have": True, "priority": 3, "resources": []}
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/roadmap")
async def generate_roadmap(
    target_career: str,
    authorization: Optional[str] = Header(None)
):
    """
    Generate a career roadmap for the target career path.
    """
    try:
        roadmap = gemini_service.generate_roadmap(analysis={}, target_career=target_career)
        
        return {
            "target_career": target_career,
            "roadmap": roadmap
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
