"""
Streaks Router
Handles user's interview streak tracking (like Duolingo)
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import date, timedelta
from core.supabase_client import supabase
from core.middleware import get_current_user, AuthenticatedUser

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


@router.get("/")
async def get_streak(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Fetch current user's streak data.
    """
    try:
        response = supabase.table("user_streaks").select("*").eq("user_id", current_user.id).execute()

        if response.data and len(response.data) > 0:
            streak_data = response.data[0]
            return {
                "current_streak": streak_data.get("current_streak", 0),
                "longest_streak": streak_data.get("longest_streak", 0),
                "last_practice_date": streak_data.get("last_practice_date"),
                "total_sessions": streak_data.get("total_sessions", 0)
            }
        else:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_practice_date": None,
                "total_sessions": 0
            }
    except Exception as e:
        print(f"Error fetching streak: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch streak data")


@router.post("/update")
async def update_streak(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update streak after completing an interview session.
    User identity comes from JWT token — not request body.
    """
    try:
        today = date.today()

        response = supabase.table("user_streaks").select("*").eq("user_id", current_user.id).execute()

        if response.data and len(response.data) > 0:
            streak_data = response.data[0]
            current_streak = streak_data.get("current_streak", 0)
            longest_streak = streak_data.get("longest_streak", 0)
            last_practice_date_str = streak_data.get("last_practice_date")

            if last_practice_date_str:
                try:
                    last_practice_date = date.fromisoformat(last_practice_date_str)
                except Exception:
                    last_practice_date = None
            else:
                last_practice_date = None

            if last_practice_date == today:
                return {
                    "current_streak": current_streak,
                    "longest_streak": longest_streak,
                    "last_practice_date": last_practice_date_str,
                    "total_sessions": streak_data.get("total_sessions", 0),
                    "message": "✅ Already practiced today!"
                }
            elif last_practice_date and last_practice_date == today - timedelta(days=1):
                new_streak = current_streak + 1
                new_longest = max(longest_streak, new_streak)
                new_total = streak_data.get("total_sessions", 0) + 1

                supabase.table("user_streaks").update({
                    "current_streak": new_streak,
                    "longest_streak": new_longest,
                    "last_practice_date": today.isoformat(),
                    "total_sessions": new_total,
                    "updated_at": "now()"
                }).eq("user_id", current_user.id).execute()

                return {
                    "current_streak": new_streak,
                    "longest_streak": new_longest,
                    "last_practice_date": today.isoformat(),
                    "total_sessions": new_total,
                    "message": f"🔥 {new_streak} day streak!"
                }
            else:
                new_total = streak_data.get("total_sessions", 0) + 1

                supabase.table("user_streaks").update({
                    "current_streak": 1,
                    "last_practice_date": today.isoformat(),
                    "total_sessions": new_total,
                    "updated_at": "now()"
                }).eq("user_id", current_user.id).execute()

                return {
                    "current_streak": 1,
                    "longest_streak": longest_streak,
                    "last_practice_date": today.isoformat(),
                    "total_sessions": new_total,
                    "message": "Don't break your streak! Come back tomorrow 💪"
                }
        else:
            supabase.table("user_streaks").insert({
                "user_id": current_user.id,
                "current_streak": 1,
                "longest_streak": 1,
                "last_practice_date": today.isoformat(),
                "total_sessions": 1
            }).execute()

            return {
                "current_streak": 1,
                "longest_streak": 1,
                "last_practice_date": today.isoformat(),
                "total_sessions": 1,
                "message": "🔥 Streak started! Keep it going!"
            }

    except Exception as e:
        print(f"Error updating streak: {e}")
        raise HTTPException(status_code=500, detail="Failed to update streak data")