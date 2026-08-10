from fastapi import APIRouter, HTTPException, Query, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.supabase_client import get_supabase
from typing import Optional, List, Any, Dict
import asyncio
import os
import logging
import uuid
from modules.interview.schemas import (
    GenerateQuestionsRequest,
    EvaluateAnswerRequest,
    SaveSessionRequest,
    QuestionHintRequest,
)
from modules.interview.manager import (
    get_interview_service,
    get_or_create_session,
)
from datetime import datetime
from dotenv import load_dotenv
from core.middleware import get_current_user, AuthenticatedUser
from core.gemini_transport import AsyncGeminiTransport
from services.interview_service import InterviewService, InterviewServiceConfig
from modules.interview.service import InterviewModuleService

interview_module_service = InterviewModuleService()
load_dotenv()

logger = logging.getLogger(__name__)
INTERVIEW_PIPELINE = "[InterviewPipeline]"

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

# # ── Supabase client ───────────────────────────────────────────────────────────
# supabase_url = os.getenv("SUPABASE_URL")
# supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
# if not supabase_url or not supabase_key:
#     raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
# supabase = create_client(supabase_url, supabase_key)

# ─────────────────────────────────────────────────────────────────────────────
# POST /generate-questions
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/generate-questions")
@limiter.limit("10/minute")
async def generate_questions(
    request: Request,
    body: GenerateQuestionsRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Generate personalized interview questions.

    Router: auth + profile fetch only.
    InterviewService: cache / throttle / AI / fallback / dedup.
    """
    if current_user.user_id != body.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    session_id = interview_module_service.get_or_create_session(
        body.user_id,
        body.career_path,
    )

    full_profile = await interview_module_service.prepare_interview_profile(
    body.user_id
    )
    if not full_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    result = await get_interview_service().generate_questions(
        user_id=body.user_id,
        career_path=body.career_path,
        difficulty=body.difficulty,
        personality=body.personality,
        interview_mode=body.interview_mode,
        profile=full_profile,
        resume_text=full_profile.get("resume_text", ""),
    )

    logger.info(
        f"{INTERVIEW_PIPELINE} user_id={body.user_id} session_id={session_id} "
        f"source={result.get('source')} "
        f"question_count={len(result.get('questions', []))} "
        f"timestamp={datetime.utcnow().isoformat()}"
    )

    if "meta" in result:
        result["meta"]["session_id"] = session_id

    return result


# ─────────────────────────────────────────────────────────────────────────────
# POST /evaluate-answer
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/evaluate-answer")
@limiter.limit("10/minute")
async def evaluate_answer(
    request: Request,
    body: EvaluateAnswerRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    if current_user.user_id != body.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await get_interview_service().evaluate_answer(
        question=body.question,
        answer=body.answer,
        career_path=body.career_path,
    )

    if not result.get("success", True) and result.get("error") in ("evaluation_failed", "rate_limit", "parse_error", "api_error"):
        raise HTTPException(
            status_code=500,
            detail="AI service is busy. Please wait a moment and try again."
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# POST /save-session
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/save-session")
async def save_session(
    body: SaveSessionRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    if user.user_id != body.user_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    try:
        loop = asyncio.get_event_loop()

        session_data = {
            "user_id": body.user_id,
            "career_path": body.career_path,
            "questions": body.questions,
            "answers": body.answers,
            "scores": body.scores,
            "total_score": body.total_score,
            "difficulty": body.difficulty,
            "interview_mode": body.interview_mode,
            "is_simulation": body.is_simulation,
            "is_voice": body.is_voice,
        }

        try:
            await interview_module_service.save_session_data(
                session_data=session_data,
                interview_rows=[]
                # interview_rows=interview_rows,
            )

        except Exception as err:
            logger.warning(f"[INTERVIEWS_INSERT] Failed: {err}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save Interview session data"
            )

        # Career Memory Engine
        try:
            from services import career_memory_engine

            await loop.run_in_executor(
                None,
                career_memory_engine.update_user_memory,
                body.user_id,
                {
                    "career_path": body.career_path,
                    "score": int(body.total_score),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        except Exception as err:
            logger.warning(
                f"[MEMORY_ENGINE] Failed: {err}"
            )

        # Career Evolution Engine
        try:
            from services import career_evolution_engine

            career_evolution_engine.update_user_evolution_profile(
                body.user_id
            )

        except Exception as err:
            logger.warning(
                f"[EVOLUTION_ENGINE] Failed: {err}"
            )

        # Badge Service
        badge_result = {
            "new_badges": [],
            "total_xp_earned": 0,
            "rank_update": None,
        }

        try:
            from services import badge_service

            badge_result = (
                badge_service.check_badges_on_session_complete(
                    user_id=body.user_id,
                    total_score=body.total_score,
                    difficulty=body.difficulty,
                    is_simulation=body.is_simulation,
                    is_voice=body.is_voice,
                )
            )

        except Exception as err:
            logger.warning(
                f"[BADGE_ERROR] Failed: {err}"
            )

        return {
            "success": True,
            "message": "Session saved successfully",
            "new_badges": badge_result.get(
                "new_badges",
                [],
            ),
            "total_xp_earned": badge_result.get(
                "total_xp_earned",
                0,
            ),
            "rank_update": badge_result.get(
                "rank_update"
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
# ─────────────────────────────────────────────────────────────────────────────
# GET /history/{user_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/history/{user_id}")
async def get_interview_history(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Get past interview sessions with pagination."""
    if user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        loop = asyncio.get_event_loop()

        count_res, page_res = await asyncio.gather(
            loop.run_in_executor(
                None,
                lambda: get_supabase().table("interview_sessions").select(
                    "career_path, total_score, created_at", count=True
                ).eq("user_id", user_id).execute()
            ),
            loop.run_in_executor(
                None,
                lambda: get_supabase().table("interview_sessions").select(
                    "career_path, total_score, created_at"
                ).eq("user_id", user_id).order("created_at", desc=True).range(
                    (page - 1) * limit, page * limit - 1
                ).execute()
            ),
        )

        total = count_res.count or 0
        sessions = list(reversed(page_res.data or []))

        return {
            "sessions": sessions,
            "count":    len(sessions),
            "pagination": {
                "page":        page,
                "limit":       limit,
                "total":       total,
                "total_pages": (total + limit - 1) // limit,
            }
        }

    except Exception as e:
        logger.error(f"[History] Error for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


# ─────────────────────────────────────────────────────────────────────────────
# POST /question-hint
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/question-hint")
@limiter.limit("10/minute")
async def get_question_hint(
    request: Request,
    body: QuestionHintRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get AI coaching hint for a question.

    FIX: was calling private gemini_service._generate() without await.
    Now uses InterviewService.get_hint() — public API, properly awaited.
    """
    return await get_interview_service().get_hint(
        question=body.question,
        career_path=body.career_path,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /progress/{user_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/progress/{user_id}")
async def get_user_progress(
    user_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Fetch user progress: sessions, rank, streaks.

    FIX: was 3 sequential DB calls. All 3 are independent — now runs
    concurrently via asyncio.gather + run_in_executor.
    Latency improvement: ~3x (parallel vs sequential).
    """
    if user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        loop = asyncio.get_event_loop()

        sessions_res, rank_res, streaks_res = await asyncio.gather(
            loop.run_in_executor(
                None,
                lambda: get_supabase().table("interview_sessions").select(
                    "career_path, total_score, created_at"
                ).eq("user_id", user_id).order("created_at", desc=True).limit(10).execute()
            ),
            loop.run_in_executor(
                None,
                lambda: get_supabase().table("user_ranks").select(
                    "xp, level, rank_title"
                ).eq("user_id", user_id).execute()
            ),
            loop.run_in_executor(
                None,
                lambda: get_supabase().table("user_streaks").select(
                    "current_streak, longest_streak, total_sessions"
                ).eq("user_id", user_id).execute()
            ),
        )

        return {
            "sessions": list(reversed(sessions_res.data or [])),
            "rank": rank_res.data[0] if rank_res.data else {
                "xp": 0, "level": 1, "rank_title": "🌱 Fresher"
            },
            "streaks": streaks_res.data[0] if streaks_res.data else {
                "current_streak": 0, "longest_streak": 0, "total_sessions": 0
            },
        }

    except Exception as e:
        logger.error(f"[Progress] Error for {user_id}: {e}")
        return {
            "sessions": [],
            "rank":    {"xp": 0, "level": 1, "rank_title": "🌱 Fresher"},
            "streaks": {"current_streak": 0, "longest_streak": 0, "total_sessions": 0},
            "error":   str(e),
        }