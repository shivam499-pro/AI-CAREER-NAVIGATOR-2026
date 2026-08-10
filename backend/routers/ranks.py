"""
Ranks Router
Handles user's rank/level and XP progression system
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.supabase_client import get_supabase
from core.middleware import get_current_user, AuthenticatedUser

router = APIRouter()


LEVELS = [
    {"level": 1, "xp_required": 0, "title": "Fresher", "emoji": "🌱"},
    {"level": 2, "xp_required": 100, "title": "Beginner", "emoji": "📚"},
    {"level": 3, "xp_required": 250, "title": "Junior", "emoji": "💼"},
    {"level": 4, "xp_required": 500, "title": "Mid-level", "emoji": "⚡"},
    {"level": 5, "xp_required": 900, "title": "Senior", "emoji": "🚀"},
    {"level": 6, "xp_required": 1400, "title": "Principal", "emoji": "👑"},
    {"level": 7, "xp_required": 2000, "title": "Legend", "emoji": "🏆"},
]


def get_level_info(xp: int):
    current_level = 1
    current_title = "Fresher"
    current_emoji = "🌱"
    next_level_xp = 100

    for i, level_info in enumerate(LEVELS):
        if xp >= level_info["xp_required"]:
            current_level = level_info["level"]
            current_title = level_info["title"]
            current_emoji = level_info["emoji"]

            if i + 1 < len(LEVELS):
                next_level_xp = LEVELS[i + 1]["xp_required"]
            else:
                next_level_xp = xp

    progress = 0
    if next_level_xp > xp:
        prev_xp = LEVELS[current_level - 1]["xp_required"]
        progress = ((xp - prev_xp) / (next_level_xp - prev_xp)) * 100

    return {
        "level": current_level,
        "title": current_title,
        "emoji": current_emoji,
        "next_level_xp": next_level_xp,
        "progress_percent": min(100, max(0, progress))
    }


def calculate_xp_earned(score: float) -> int:
    if score >= 80:
        return 50
    elif score >= 60:
        return 35
    elif score >= 40:
        return 20
    else:
        return 10


class UpdateRankRequest(BaseModel):
    score: float


@router.get("/{user_id}")
async def get_rank(user_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's rank.")

    supabase = get_supabase()
    try:
        response = supabase.table("user_ranks").select("*").eq("user_id", user_id).execute()

        if response.data and len(response.data) > 0:
            rank_data = response.data[0]
            xp = rank_data.get("xp", 0)
            level_info = get_level_info(xp)

            return {
                "xp": xp,
                "level": level_info["level"],
                "rank_title": f"{level_info['emoji']} {level_info['title']}",
                "next_level_xp": level_info["next_level_xp"],
                "progress_percent": level_info["progress_percent"]
            }
        else:
            return {
                "xp": 0, "level": 1, "rank_title": "🌱 Fresher",
                "next_level_xp": 100, "progress_percent": 0
            }
    except Exception as e:
        print(f"Error fetching rank: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch rank data")


@router.post("/update")
async def update_rank(body: UpdateRankRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    supabase = get_supabase()
    try:
        user_id = current_user.user_id
        score = body.score
        xp_earned = calculate_xp_earned(score)

        response = supabase.table("user_ranks").select("*").eq("user_id", user_id).execute()

        if response.data and len(response.data) > 0:
            rank_data = response.data[0]
            current_xp = rank_data.get("xp", 0)
            new_xp = current_xp + xp_earned

            old_level_info = get_level_info(current_xp)
            new_level_info = get_level_info(new_xp)
            leveled_up = new_level_info["level"] > old_level_info["level"]

            supabase.table("user_ranks").update({
                "xp": new_xp,
                "level": new_level_info["level"],
                "rank_title": f"{new_level_info['emoji']} {new_level_info['title']}",
                "updated_at": "now()"
            }).eq("user_id", user_id).execute()

            return {
                "xp": new_xp,
                "level": new_level_info["level"],
                "rank_title": f"{new_level_info['emoji']} {new_level_info['title']}",
                "xp_earned": xp_earned,
                "leveled_up": leveled_up,
                "next_level_xp": new_level_info["next_level_xp"]
            }
        else:
            level_info = get_level_info(xp_earned)

            insert_result = supabase.table("user_ranks").insert({
                "user_id": user_id,
                "xp": xp_earned,
                "level": level_info["level"],
                "rank_title": f"{level_info['emoji']} {level_info['title']}"
            }).execute()

            return {
                "xp": xp_earned,
                "level": level_info["level"],
                "rank_title": f"{level_info['emoji']} {level_info['title']}",
                "xp_earned": xp_earned,
                "leveled_up": level_info["level"] > 1,
                "next_level_xp": level_info["next_level_xp"]
            }

    except Exception as e:
        print(f"Error updating rank: {e}")
        raise HTTPException(status_code=500, detail="Failed to update rank data")