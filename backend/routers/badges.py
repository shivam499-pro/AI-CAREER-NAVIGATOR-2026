"""
Badges Router
Handles user achievement badges system.
GET  /{user_id}  — fetch earned + all badges (paginated)
POST /check      — trigger badge check, delegates to badge_service
"""
import logging
import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from core.supabase_client import get_supabase

from core.middleware import get_current_user, AuthenticatedUser
from services.badge_service import check_and_award_badges, BADGES


load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()

# ─── Constants ────────────────────────────────────────────────────────────────

VALID_EVENTS = frozenset({
    "session_complete",
    "perfect_score",
    "hard_mode",
    "simulation",
    "voice_used",
    "challenge_created",
    "challenge_won",
    "streak_milestone",
})


# ─── Request Models ───────────────────────────────────────────────────────────

class CheckBadgeRequest(BaseModel):
    user_id: str
    event: str


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/{user_id}")
async def get_user_badges(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Fetch user's earned badges with pagination.
    Returns: { earned, all_badges, pagination }
    """
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        # Total count of earned badges
        count_response = get_supabase().table("user_badges").select(
            "*", count=True
        ).eq("user_id", user_id).execute()

        total = count_response.count or 0
        total_pages = (total + limit - 1) // limit

        # Paginated earned badges
        response = get_supabase().table("user_badges").select("*").eq(
            "user_id", user_id
        ).range(
            (page - 1) * limit,
            page * limit - 1
        ).execute()

        # Build earned list — BADGES dict is the single source of truth
        earned_badges = []
        if response.data:
            for record in response.data:
                badge_id = record.get("badge_id")
                badge_def = BADGES.get(badge_id)
                if badge_def:
                    earned_badges.append({
                        "badge_id": badge_id,
                        "name": badge_def["name"],
                        "emoji": badge_def["emoji"],
                        "description": badge_def["description"],
                        "earned_at": record.get("earned_at")
                    })

        # Full catalogue — BADGES dict is the single source of truth
        all_badges = [
            {**v, "badge_id": v["id"]} for v in BADGES.values()
        ]

        return {
            "earned": earned_badges,
            "all_badges": all_badges,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages
            }
        }

    except Exception as e:
        logger.error(f"Error fetching badges for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch badges")


@router.post("/check")
async def check_and_award_badges_endpoint(
    request: CheckBadgeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Trigger badge check after a user action.
    Delegates entirely to badge_service.check_and_award_badges.
    Returns: { newly_earned: [...badges] }
    """
    if current_user.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Fix #6 — validate event before hitting the service
    if request.event not in VALID_EVENTS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event '{request.event}'. Must be one of: {sorted(VALID_EVENTS)}"
        )

    result = check_and_award_badges(
        user_id=request.user_id,
        event=request.event
    )

    return {
        "newly_earned": result.get("new_badges", [])
    }