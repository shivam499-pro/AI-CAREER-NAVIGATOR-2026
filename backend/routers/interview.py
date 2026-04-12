"""
Interview Router
Handles AI interview practice functionality
"""
from fastapi import APIRouter, HTTPException, Query, Request, Header, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from supabase import create_client
import os
import time
import logging
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Structured log prefix
INTERVIEW_PIPELINE_LOG = "[INTERVIEW_PIPELINE]"

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
supabase = create_client(supabase_url, supabase_key)

# =============================================================================
# STABILITY IMPROVEMENTS: Cache, Throttling, and Fallbacks
# =============================================================================

# In-memory cache for generated interview questions
# Key: user_id + career_path + difficulty
# TTL: 15 minutes (900 seconds)
_questions_cache: Dict[str, tuple] = {}  # {cache_key: (timestamp, questions)}
QUESTIONS_CACHE_TTL = 900  # 15 minutes

# Request throttling per user
# Prevent same user from calling generate-questions more than once within 20 seconds
_user_last_request_time: Dict[str, float] = {}
USER_THROTTLE_SECONDS = 20

# Session creation tracking to prevent duplicate sessions
# Key: user_id + career_path -> session_id
_user_active_sessions: Dict[str, str] = {}

# Fallback question bank (used when Gemini + cache both fail)
FALLBACK_QUESTIONS = [
    {
        "id": 1,
        "question": "Tell me about yourself and why you're interested in this role.",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Focus on your background, key skills, and why this career path interests you."
    },
    {
        "id": 2,
        "question": "Describe a challenging project you worked on. What was the problem and how did you solve it?",
        "type": "project_based",
        "difficulty": "medium",
        "hint": "Use STAR method: Situation, Task, Action, Result. Be specific about your contribution."
    },
    {
        "id": 3,
        "question": "What are your strengths and how do they help you in this role?",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Pick 2-3 relevant strengths with concrete examples from your experience."
    },
    {
        "id": 4,
        "question": "Where do you see yourself in 5 years?",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Align your answer with the career path and show ambition balanced with realism."
    },
    {
        "id": 5,
        "question": "Describe a time when you had to learn something new quickly. How did you approach it?",
        "type": "behavioral",
        "difficulty": "medium",
        "hint": "Show your learning ability and adaptability. Include specific steps you took."
    },
    {
        "id": 6,
        "question": "What are your salary expectations?",
        "type": "behavioral",
        "difficulty": "medium",
        "hint": "Research the market rate for your role and experience level. Give a range."
    },
    {
        "id": 7,
        "question": "Why do you want to work at this company?",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Research the company. Mention specific values, products, or recent achievements."
    },
    {
        "id": 8,
        "question": "Tell me about a time you failed and what you learned from it.",
        "type": "behavioral",
        "difficulty": "medium",
        "hint": "Be honest but focus on what you learned and how you improved afterward."
    },
    {
        "id": 9,
        "question": "What questions do you have for me?",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Ask about team culture, immediate priorities, or growth opportunities. Avoid salary/leave in first round."
    },
    {
        "id": 10,
        "question": "Describe a technical problem you solved. What was your approach?",
        "type": "technical",
        "difficulty": "medium",
        "hint": "Explain the problem clearly, walk through your solution, and mention the outcome."
    }
]


def _get_questions_cache_key(user_id: str, career_path: str, difficulty: str) -> str:
    """Generate cache key from user_id, career_path, and difficulty."""
    return f"{user_id}:{career_path}:{difficulty}"


def _get_cached_questions(user_id: str, career_path: str, difficulty: str) -> Optional[List[Dict]]:
    """Get cached questions if valid (not expired)."""
    global _questions_cache
    cache_key = _get_questions_cache_key(user_id, career_path, difficulty)
    
    if cache_key in _questions_cache:
        timestamp, questions = _questions_cache[cache_key]
        current_time = time.time()
        if current_time - timestamp <= QUESTIONS_CACHE_TTL:
            return questions
        else:
            # Expired - remove it
            del _questions_cache[cache_key]
    
    return None


def _set_cached_questions(user_id: str, career_path: str, difficulty: str, questions: List[Dict]) -> None:
    """Store questions in cache with current timestamp."""
    global _questions_cache
    cache_key = _get_questions_cache_key(user_id, career_path, difficulty)
    _questions_cache[cache_key] = (time.time(), questions)


def _check_user_throttle(user_id: str) -> bool:
    """Check if user is within throttle period. Returns True if throttled."""
    global _user_last_request_time
    current_time = time.time()
    
    if user_id in _user_last_request_time:
        time_since_last = current_time - _user_last_request_time[user_id]
        if time_since_last < USER_THROTTLE_SECONDS:
            return True
    
    # Update last request time
    _user_last_request_time[user_id] = current_time
    return False


def _get_fallback_questions() -> List[Dict]:
    """Get the static fallback question bank."""
    return FALLBACK_QUESTIONS


def _deduplicate_questions(questions: List[Dict]) -> List[Dict]:
    """
    Deduplicate questions based on question text.
    Returns unique questions while preserving order.
    """
    seen = set()
    unique_questions = []
    
    for q in questions:
        # Use normalized question text as dedup key
        question_text = q.get("question", "").strip().lower()
        if question_text and question_text not in seen:
            seen.add(question_text)
            unique_questions.append(q)
    
    return unique_questions


def _log_pipeline(
    user_id: str,
    session_id: str | None,
    source: str,
    retry_used: bool,
    question_count: int
) -> None:
    """
    Structured debug trace logging for interview pipeline.
    Format: [INTERVIEW_PIPELINE] user_id=... session_id=... source=... retry_used=... question_count=... timestamp=...
    """
    logger.info(
        f"{INTERVIEW_PIPELINE} user_id={user_id} session_id={session_id or 'N/A'} "
        f"source={source} retry_used={retry_used} question_count={question_count} "
        f"timestamp={datetime.utcnow().isoformat()}"
    )


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
async def generate_questions(request: Request, body: GenerateQuestionsRequest):
    """
    Generate 5 personalized interview questions based on user profile.
    
    Implements:
    - In-memory cache with 15-minute TTL
    - Request throttling per user (20 seconds)
    - Safe retry logic (retry once on Gemini failure)
    - Question deduplication
    - Fallback question bank when Gemini + cache fail
    - Comprehensive logging with structured pipeline logs
    - Always returns 200 OK with valid structure
    """
    # Generate or reuse session ID for this user+career_path combination
    session_key = f"{body.user_id}:{body.career_path}"
    if session_key not in _user_active_sessions:
        _user_active_sessions[session_key] = str(uuid.uuid4())
    session_id = _user_active_sessions[session_key]
    
    try:
        # STEP 1: Check request throttling (20 seconds per user)
        if _check_user_throttle(body.user_id):
            # User is within throttle period - try to return cached response
            cached = _get_cached_questions(body.user_id, body.career_path, body.difficulty)
            if cached:
                logger.info(f"[Interview] Cache hit (throttled user) for {body.user_id}:{body.career_path}")
                _log_pipeline(body.user_id, session_id, "throttle_cache", False, len(cached))
                return {
                    "success": True,
                    "questions": cached,
                    "source": "throttle_cache",
                    "meta": {"cached": True, "retry_used": False, "session_id": session_id}
                }
            # No cache available, return fallback
            logger.warning(f"[Interview] Throttled user with no cache: {body.user_id}")
            fallback_q = _get_fallback_questions()
            _log_pipeline(body.user_id, session_id, "throttle_fallback", False, len(fallback_q))
            return {
                "success": True,
                "questions": fallback_q,
                "source": "throttle_fallback",
                "meta": {"cached": False, "retry_used": False, "session_id": session_id}
            }
        
        # STEP 2: Check cache first (15-minute TTL)
        cached = _get_cached_questions(body.user_id, body.career_path, body.difficulty)
        if cached:
            logger.info(f"[Interview] Cache hit for {body.user_id}:{body.career_path}")
            _log_pipeline(body.user_id, session_id, "cache", False, len(cached))
            return {
                "success": True,
                "questions": cached,
                "source": "cache",
                "meta": {"cached": True, "retry_used": False, "session_id": session_id}
            }
        
        # STEP 3: Cache miss - fetch user data and prepare for Gemini call
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
        
        # STEP 4: Call Gemini to generate questions (with retry on failure)
        questions = None
        retry_used = False
        
        try:
            # First attempt
            logger.info(f"[Interview] Calling Gemini for {body.user_id}:{body.career_path} (attempt 1)")
            questions = gemini_service.generate_interview_questions(
                full_profile, 
                body.career_path,
                body.difficulty,
                full_profile.get("resume_text", ""),
                body.personality
            )
        except Exception as gemini_error:
            error_str = str(gemini_error).lower()
            if "rate limit" in error_str or "429" in error_str:
                logger.warning(f"[Interview] Gemini rate limit on attempt 1, retrying: {gemini_error}")
                retry_used = True
                try:
                    # Retry once
                    time.sleep(1)  # Brief delay before retry
                    logger.info(f"[Interview] Retrying Gemini for {body.user_id}:{body.career_path} (attempt 2)")
                    questions = gemini_service.generate_interview_questions(
                        full_profile, 
                        body.career_path,
                        body.difficulty,
                        full_profile.get("resume_text", ""),
                        body.personality
                    )
                except Exception as retry_error:
                    logger.error(f"[Interview] Gemini retry failed: {retry_error}")
                    questions = None
            else:
                raise
        
        # STEP 5: Check if Gemini returned valid questions
        if questions and len(questions) > 0:
            # Deduplicate questions
            unique_questions = _deduplicate_questions(questions)
            
            # If deduplication removed too many questions, pad with fallback
            if len(unique_questions) < 3:
                logger.warning(f"[Interview] Few unique questions ({len(unique_questions)}), using fallback")
                fallback = _get_fallback_questions()
                # Add some fallback questions to fill gaps
                unique_questions.extend(fallback[:5 - len(unique_questions)])
            
            # Re-index questions to ensure sequential IDs
            for i, q in enumerate(unique_questions, 1):
                q["id"] = i
            
            # Store in cache
            _set_cached_questions(body.user_id, body.career_path, body.difficulty, unique_questions)
            logger.info(f"[Interview] Successfully generated {len(unique_questions)} questions for {body.user_id}")
            logger.info(f"[Interview] source used: gemini, questions count: {len(unique_questions)}")
            _log_pipeline(body.user_id, session_id, "gemini", retry_used, len(unique_questions))
            return {
                "success": True,
                "questions": unique_questions,
                "source": "gemini",
                "meta": {"cached": False, "retry_used": retry_used, "session_id": session_id}
            }
        
        # STEP 6: Gemini failed - check if there's a previous cache we can use
        # (even if expired, it's better than nothing)
        cached_expired = _get_cached_questions(body.user_id, body.career_path, body.difficulty)
        if cached_expired:
            logger.info(f"[Interview] Using expired cache for {body.user_id}")
            logger.info(f"[Interview] source used: expired_cache, questions count: {len(cached_expired)}")
            _log_pipeline(body.user_id, session_id, "expired_cache", retry_used, len(cached_expired))
            return {
                "success": True,
                "questions": cached_expired,
                "source": "expired_cache",
                "meta": {"cached": True, "retry_used": retry_used, "session_id": session_id}
            }
        
        # STEP 7: All options exhausted - return fallback questions
        logger.warning(f"[Interview] Gemini failed and no cache - serving fallback questions")
        fallback_q = _get_fallback_questions()
        logger.info(f"[Interview] source used: fallback, questions count: {len(fallback_q)}")
        _log_pipeline(body.user_id, session_id, "fallback", retry_used, len(fallback_q))
        return {
            "success": True,
            "questions": fallback_q,
            "source": "fallback",
            "meta": {"cached": False, "retry_used": retry_used, "session_id": session_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        # Check if it's a rate limit error
        if "rate limit" in error_str or "429" in error_str:
            logger.warning(f"[Interview] Rate limit error - serving fallback: {str(e)}")
            
            # Try to return cached questions
            cached = _get_cached_questions(body.user_id, body.career_path, body.difficulty)
            if cached:
                _log_pipeline(body.user_id, session_id, "error_cache", False, len(cached))
                return {
                    "success": True,
                    "questions": cached,
                    "source": "error_cache",
                    "meta": {"cached": True, "retry_used": False, "session_id": session_id}
                }
            
            # Return fallback questions - never crash
            fallback_q = _get_fallback_questions()
            _log_pipeline(body.user_id, session_id, "error_fallback", False, len(fallback_q))
            return {
                "success": True,
                "questions": fallback_q,
                "source": "error_fallback",
                "meta": {"cached": False, "retry_used": False, "session_id": session_id}
            }
        
        logger.error(f"[Interview] Unexpected error in generate-questions: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # For any other error, try to return cached or fallback - never crash frontend
        cached = _get_cached_questions(body.user_id, body.career_path, body.difficulty)
        if cached:
            _log_pipeline(body.user_id, session_id, "exception_cache", False, len(cached))
            return {
                "success": True,
                "questions": cached,
                "source": "exception_cache",
                "meta": {"cached": True, "retry_used": False, "session_id": session_id}
            }
        
        fallback_q = _get_fallback_questions()
        _log_pipeline(body.user_id, session_id, "exception_fallback", False, len(fallback_q))
        return {
            "success": True,
            "questions": fallback_q,
            "source": "exception_fallback",
            "meta": {"cached": False, "retry_used": False, "session_id": session_id}
        }


@router.post("/evaluate-answer")
@limiter.limit("10/minute")
async def evaluate_answer(request: Request, body: EvaluateAnswerRequest):
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


def get_current_user(authorization: str = Header(None)) -> str:
    """
    Dependency to extract and verify the JWT token from Authorization header.
    Returns the user_id from the token.
    Raises HTTPException 401 if token is missing or invalid.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_response.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/save-session")
async def save_session(body: SaveSessionRequest, current_user_id: str = Depends(get_current_user)):
    """
    Save an interview session to the database.
    """
    # Verify the user_id from the token matches the body
    if current_user_id != body.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
        
        # =============================================================================
        # CAREER MEMORY ENGINE INTEGRATION (Non-critical)
        # Update user memory after successful session save.
        # DO NOT block response if memory update fails.
        # =============================================================================
        try:
            from services import career_memory_engine
            
            # Prepare session data for memory engine
            memory_session_data = {
                "career_path": body.career_path,
                "score": int(body.total_score),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Update user memory (non-blocking)
            career_memory_engine.update_user_memory(
                body.user_id,
                memory_session_data
            )
        except Exception as memory_error:
            # Log error but do NOT block the response
            logger.warning(f"[MEMORY_ENGINE_ERROR] Failed to update memory: {str(memory_error)}")
        # =============================================================================
        # END CAREER MEMORY INTEGRATION
        # =============================================================================
        
        # =============================================================================
        # CAREER EVOLUTION ENGINE INTEGRATION (Non-critical)
        # Invalidate evolution cache after session.
        # DO NOT block response if update fails.
        # =============================================================================
        try:
            from services import career_evolution_engine
            
            # Update evolution profile cache (non-blocking)
            career_evolution_engine.update_user_evolution_profile(
                body.user_id
            )
        except Exception as evolution_error:
            # Log error but do NOT block the response
            logger.warning(f"[EVOLUTION_ENGINE_ERROR] Failed to update profile: {str(evolution_error)}")
        # =============================================================================
        # END CAREER EVOLUTION INTEGRATION
        # =============================================================================
        
        return {"success": True, "message": "Session saved successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}")
async def get_interview_history(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    current_user_id: str = Depends(get_current_user)
):
    """
    Get past interview sessions for a user with pagination.
    """
    # Verify the user_id from the token matches the requested user_id
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
        raise HTTPException(status_code=500, detail=str(e))


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
async def get_user_progress(user_id: str, current_user_id: str = Depends(get_current_user)):
    """
    Fetch user's progress data including sessions, rank, and streaks.
    """
    # Verify the user_id from the token matches the requested user_id
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
