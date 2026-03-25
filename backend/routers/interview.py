"""
Interview Router
Handles AI interview practice functionality
"""
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from typing import Optional, List, Any
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


class GenerateQuestionsRequest(BaseModel):
    user_id: str
    career_path: str
    difficulty: str = "medium"


class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str
    career_path: str
    user_id: str


class SaveSessionRequest(BaseModel):
    user_id: str
    career_path: str
    questions: List[Any]
    answers: List[Any]
    scores: List[Any]
    total_score: float


@router.post("/generate-questions")
@limiter.limit("10/minute")
async def generate_questions(request: Request, body: GenerateQuestionsRequest):
    """
    Generate 5 personalized interview questions based on user profile.
    """
    try:
        # Fetch user data
        profile_response = supabase.table("profiles").select("*").eq("user_id", request.user_id).execute()
        
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = profile_response.data[0]
        
        # Fetch analysis data for strengths
        analysis_response = supabase.table("analyses").select("*").eq("user_id", request.user_id).execute()
        
        analysis_data = {}
        if analysis_response.data:
            analysis_data = analysis_response.data[0]
        
        # Build full profile for questions
        full_profile = {
            "college_name": profile.get("college_name"),
            "degree": profile.get("degree"),
            "branch": profile.get("branch"),
            "extra_skills": profile.get("extra_skills", []),
            "experience": profile.get("experience", []),
            "certificates": profile.get("certificates", []),
            "career_goal": profile.get("career_goal"),
            "resume_text": profile.get("resume_text"),
            "github_username": profile.get("github_username"),
        }
        
        # Add analysis data
        if analysis_data:
            full_profile["strengths"] = analysis_data.get("analysis", {}).get("strengths", [])
            full_profile["career_paths"] = analysis_data.get("career_paths", [])
        
        # Import and call gemini service
        from services import gemini_service
        questions = gemini_service.generate_interview_questions(
            full_profile, 
            request.career_path, 
            request.difficulty,
            full_profile.get("resume_text", "")
        )
        
        return {"questions": questions}
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-answer")
async def evaluate_answer(request: EvaluateAnswerRequest):
    """
    Evaluate a user's interview answer.
    """
    try:
        from services import gemini_service
        result = gemini_service.evaluate_interview_answer(
            request.question,
            request.answer,
            request.career_path
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-session")
async def save_session(request: SaveSessionRequest):
    """
    Save an interview session to the database.
    """
    try:
        session_data = {
            "user_id": request.user_id,
            "career_path": request.career_path,
            "questions": request.questions,
            "answers": request.answers,
            "scores": request.scores,
            "total_score": request.total_score
        }
        
        response = supabase.table("interview_sessions").insert(session_data).execute()
        
        return {"success": True, "message": "Session saved successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}")
async def get_interview_history(user_id: str):
    """
    Get past interview sessions for a user.
    """
    try:
        response = supabase.table("interview_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        return {
            "sessions": response.data,
            "count": len(response.data) if response.data else 0
        }
        
    except Exception as e:
        return {"sessions": [], "count": 0, "error": str(e)}
