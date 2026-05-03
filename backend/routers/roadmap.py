"""
Roadmap Progress Router
Tracks user milestone completion for career roadmaps.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from core.middleware import get_current_user, AuthenticatedUser, APIResponse
from core.supabase_client import get_supabase

router = APIRouter()


class MilestoneUpdate(BaseModel):
    career_path: str
    milestone_week: int
    status: str  # pending / in_progress / completed
    notes: Optional[str] = None


@router.patch("/milestone")
async def update_milestone(
    payload: MilestoneUpdate,
    user: AuthenticatedUser = Depends(get_current_user)
):
    try:
        supabase = get_supabase()

        # Time-gate: only apply when marking as completed
        if payload.status == "completed":
            last = supabase.table("roadmap_progress") \
                .select("completed_at") \
                .eq("user_id", user.user_id) \
                .eq("career_path", payload.career_path) \
                .eq("status", "completed") \
                .order("completed_at", desc=True) \
                .limit(1) \
                .execute()

            if last.data and last.data[0].get("completed_at"):
                last_completed = datetime.fromisoformat(
                    last.data[0]["completed_at"].replace("Z", "+00:00")
                )
                from datetime import timezone
                days_since = (datetime.now(timezone.utc) - last_completed).days
                if days_since < 3:
                    return JSONResponse(
                    status_code=429,
                    content=APIResponse.error_response(
                        f"Wait {3 - days_since} more day(s) before completing the next milestone.",
                        code="TOO_SOON"
                    )
                )
        data = {
            "user_id": user.user_id,
            "career_path": payload.career_path,
            "milestone_week": payload.milestone_week,
            "status": payload.status,
            "notes": payload.notes,
            "updated_at": datetime.utcnow().isoformat(),
        }

        if payload.status == "completed":
            data["completed_at"] = datetime.utcnow().isoformat()

        supabase.table("roadmap_progress").upsert(
            data,
            on_conflict="user_id,career_path,milestone_week"
        ).execute()

        # Check if all milestones for this career path are completed
        all_progress = supabase.table("roadmap_progress") \
            .select("status") \
            .eq("user_id", user.user_id) \
            .eq("career_path", payload.career_path) \
            .execute()

        total = len(all_progress.data) if all_progress.data else 0
        completed = sum(1 for r in all_progress.data if r["status"] == "completed") if all_progress.data else 0

        roadmap_completed = total > 0 and completed == total

        return APIResponse.success_response(data={
            "updated": True,
            "career_path": payload.career_path,
            "milestone_week": payload.milestone_week,
            "status": payload.status,
            "completed_count": completed,
            "total_count": total,
            "roadmap_completed": roadmap_completed
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(str(e), code="MILESTONE_UPDATE_ERROR")
        )


@router.get("/progress/{career_path}")
async def get_roadmap_progress(
    career_path: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    try:
        supabase = get_supabase()

        response = supabase.table("roadmap_progress") \
            .select("*") \
            .eq("user_id", user.user_id) \
            .eq("career_path", career_path) \
            .execute()

        progress = response.data or []
        completed = sum(1 for r in progress if r["status"] == "completed")
        in_progress = sum(1 for r in progress if r["status"] == "in_progress")

        # Build a dict keyed by week for easy frontend lookup
        progress_map = {r["milestone_week"]: r["status"] for r in progress}

        return APIResponse.success_response(data={
            "career_path": career_path,
            "progress_map": progress_map,
            "completed_count": completed,
            "in_progress_count": in_progress,
            "total_tracked": len(progress),
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(str(e), code="PROGRESS_FETCH_ERROR")
        )