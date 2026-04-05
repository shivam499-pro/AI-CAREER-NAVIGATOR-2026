"""
Interview Router
Handles AI interview practice functionality
"""
from fastapi import APIRouter, HTTPException, Query
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
    personality: str = "friendly"


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


class QuestionHintRequest(BaseModel):
    question: str
    career_path: str


@router.post("/generate-questions")
@limiter.limit("10/minute")
async def generate_questions(body: GenerateQuestionsRequest):
    """
    Generate 5 personalized interview questions based on user profile.
    """
    try:
        # Fetch user data
        profile_response = supabase.table("profiles").select("*").eq("user_id", body.user_id).execute()

        if not profile_response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = profile_response.data[0]
        
        # Fetch analysis data for strengths
        analysis_response = supabase.table("analyses").select("*").eq("user_id", body.user_id).execute()
        
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
        
        # FIX: Use 'body' instead of 'request' to access your Pydantic data
        questions = gemini_service.generate_interview_questions(
            full_profile, 
            body.career_path,  # Changed from request.career_path
            body.difficulty,   # Changed from request.difficulty
            full_profile.get("resume_text", ""),
            body.personality
        )
        
        return {"questions": questions}
        
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        # Check if it's a rate limit error
        if "rate limit" in error_str or "429" in error_str:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "The AI service is currently busy. Please wait a moment and try again.",
                    "error_type": "rate_limit",
                    "suggestion": "Wait 30-60 seconds before retrying your request."
                }
            )
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-answer")
async def evaluate_answer(body : EvaluateAnswerRequest):
    """
    Evaluate a user's interview answer.
    """
    try:
        from services import gemini_service
        result = gemini_service.evaluate_interview_answer(
            body.question,
            body.answer,
            body.career_path
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-session")
async def save_session(body: SaveSessionRequest):
    """
    Save an interview session to the database.
    """
    try:
        session_data = {
            "user_id": body.user_id,
            "career_path": body.career_path,
            "questions": body.questions,
            "answers": body.answers,
            "scores": body.scores,
            "total_score": body.total_score
        }
        
        supabase.table("interview_sessions").insert(session_data).execute()
        
        return {"success": True, "message": "Session saved successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}")
async def get_interview_history(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page")
):
    """
    Get past interview sessions for a user with pagination.
    """
    try:
        # Get total count
        count_response = supabase.table("interview_sessions").select(
            "career_path, total_score, created_at",
            count=True
        ).eq("user_id", user_id).execute()
        
        total = count_response.count or 0
        total_pages = (total + limit - 1) // limit
        
        # Get paginated results
        response = supabase.table("interview_sessions").select(
            "career_path, total_score, created_at"
        ).eq("user_id", user_id).order("created_at", desc=True).range(
            (page - 1) * limit,
            page * limit - 1
        ).execute()
        
        sessions = response.data if response.data else []
        # Reverse to show oldest to newest for chart
        sessions = list(reversed(sessions))
        
        return {
            "sessions": sessions,
            "count": len(sessions),
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages
            }
        }
        
    except Exception as e:
        return {
            "sessions": [],
            "count": 0,
            "error": str(e),
            "pagination": {"page": page, "limit": limit, "total": 0, "total_pages": 0}
        }


@router.post("/question-hint")
async def get_question_hint(body: QuestionHintRequest):
    """
    Get AI coaching hint for a specific interview question.
    """
    try:
        from services import gemini_service
        
        prompt = f"""You are an expert interview coach. For this interview question: 
'{body.question}' for a '{body.career_path}' role, provide:
1. What the interviewer is looking for (2-3 points)
2. How to structure the answer (method like STAR, etc.)
3. A short example direction (2-3 sentences)

Keep it concise and practical.

Return ONLY a valid JSON object with exactly these fields:
{{"looking_for": "...", "structure": "...", "example": "..."}}
No other text or markdown."""
        
        # Use the existing generate method from gemini_service
        response = gemini_service._generate(prompt)
        
        # Parse the JSON response
        import json
        import re
        
        # Clean the response
        text = response.strip()
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        result = json.loads(text)
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "looking_for": "Focus on demonstrating your skills and experience.",
            "structure": "Use STAR method (Situation, Task, Action, Result).",
            "example": "Start with a brief context, then describe your specific contribution."
        }


@router.get("/progress/{user_id}")
async def get_user_progress(user_id: str):
    """
    Fetch user's progress data including sessions, rank, and streaks.
    """
    try:
        # Fetch last 10 sessions
        sessions_response = supabase.table("interview_sessions").select(
            "career_path, total_score, created_at"
        ).eq("user_id", user_id).order("created_at", desc=True).limit(10).execute()
        
        sessions = sessions_response.data if sessions_response.data else []
        # Reverse to show oldest to newest for chart
        sessions = list(reversed(sessions))
        
        # Fetch user rank
        rank_response = supabase.table("user_ranks").select(
            "xp, level, rank_title"
        ).eq("user_id", user_id).execute()
        
        rank = rank_response.data[0] if rank_response.data else {
            "xp": 0,
            "level": 1,
            "rank_title": "🌱 Fresher"
        }
        
        # Fetch user streaks
        streaks_response = supabase.table("user_streaks").select(
            "current_streak, longest_streak, total_sessions"
        ).eq("user_id", user_id).execute()
        
        streaks = streaks_response.data[0] if streaks_response.data else {
            "current_streak": 0,
            "longest_streak": 0,
            "total_sessions": 0
        }
        
        return {
            "sessions": sessions,
            "rank": rank,
            "streaks": streaks
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "sessions": [],
            "rank": {"xp": 0, "level": 1, "rank_title": "🌱 Fresher"},
            "streaks": {"current_streak": 0, "longest_streak": 0, "total_sessions": 0},
            "error": str(e)
        }
