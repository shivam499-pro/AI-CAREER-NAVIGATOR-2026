"""
Streaks Router
Handles user's interview streak tracking (like Duolingo)
"""
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import date, timedelta

# Load environment variables
load_dotenv()

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)


class UpdateStreakRequest(BaseModel):
    user_id: str


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_practice_date: str | None
    total_sessions: int
    message: str | None = None


@router.get("/{user_id}")
async def get_streak(user_id: str):
    """
    Fetch user's current streak data from Supabase table "user_streaks"
    """
    try:
        response = supabase.table("user_streaks").select("*").eq("user_id", user_id).execute()
        
        if response.data and len(response.data) > 0:
            streak_data = response.data[0]
            return {
                "current_streak": streak_data.get("current_streak", 0),
                "longest_streak": streak_data.get("longest_streak", 0),
                "last_practice_date": streak_data.get("last_practice_date"),
                "total_sessions": streak_data.get("total_sessions", 0)
            }
        else:
            # No streak record exists yet - return default values
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
async def update_streak(request: Request, body: UpdateStreakRequest):
    """
    Update user's streak after completing an interview session
    """
    try:
        user_id = body.user_id
        today = date.today()
        
        # Try to get existing streak data
        response = supabase.table("user_streaks").select("*").eq("user_id", user_id).execute()
        
        if response.data and len(response.data) > 0:
            streak_data = response.data[0]
            current_streak = streak_data.get("current_streak", 0)
            longest_streak = streak_data.get("longest_streak", 0)
            last_practice_date_str = streak_data.get("last_practice_date")
            
            # Parse last practice date if it exists
            if last_practice_date_str:
                try:
                    last_practice_date = date.fromisoformat(last_practice_date_str)
                except:
                    last_practice_date = None
            else:
                last_practice_date = None
            
            # Calculate new streak
            if last_practice_date == today:
                # Already practiced today
                return {
                    "current_streak": current_streak,
                    "longest_streak": longest_streak,
                    "last_practice_date": last_practice_date_str,
                    "total_sessions": streak_data.get("total_sessions", 0),
                    "message": "✅ Already practiced today!"
                }
            elif last_practice_date and last_practice_date == today - timedelta(days=1):
                # Practiced yesterday - increment streak
                new_streak = current_streak + 1
                new_longest = max(longest_streak, new_streak)
                new_total = streak_data.get("total_sessions", 0) + 1
                
                supabase.table("user_streaks").update({
                    "current_streak": new_streak,
                    "longest_streak": new_longest,
                    "last_practice_date": today.isoformat(),
                    "total_sessions": new_total,
                    "updated_at": "now()"
                }).eq("user_id", user_id).execute()
                
                return {
                    "current_streak": new_streak,
                    "longest_streak": new_longest,
                    "last_practice_date": today.isoformat(),
                    "total_sessions": new_total,
                    "message": f"🔥 Streak updated! You're on a {new_streak} day streak!"
                }
            else:
                # Last practice was older than yesterday - reset streak
                new_total = streak_data.get("total_sessions", 0) + 1
                
                supabase.table("user_streaks").update({
                    "current_streak": 1,
                    "last_practice_date": today.isoformat(),
                    "total_sessions": new_total,
                    "updated_at": "now()"
                }).eq("user_id", user_id).execute()
                
                if last_practice_date:
                    return {
                        "current_streak": 1,
                        "longest_streak": longest_streak,
                        "last_practice_date": today.isoformat(),
                        "total_sessions": new_total,
                        "message": "Don't break your streak! Come back tomorrow 💪"
                    }
                else:
                    return {
                        "current_streak": 1,
                        "longest_streak": longest_streak,
                        "last_practice_date": today.isoformat(),
                        "total_sessions": new_total,
                        "message": "🔥 Streak started! Keep it going!"
                    }
        else:
            # No record exists - create new one
            supabase.table("user_streaks").insert({
                "user_id": user_id,
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