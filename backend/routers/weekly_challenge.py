from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)


class SubmitWeeklyChallengeRequest(BaseModel):
    user_id: str
    score: float
    answers: list


class StartChallengeRequest(BaseModel):
    user_id: str
    week_number: int
    year: int


def get_current_week_info():
    """Get current week number and year, along with start/end dates."""
    now = datetime.utcnow()
    # Get the Monday of the current week
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Calculate week number (ISO week)
    week_number = now.isocalendar()[1]
    year = now.year
    
    return week_number, year, week_start, week_end


@router.get("/current")
async def get_current_week_challenge():
    """
    Get current week's challenge.
    If not exists, auto-create one.
    Returns: { week_number, year, theme, career_path, questions, ends_at }
    """
    try:
        week_number, year, week_start, week_end = get_current_week_info()
        
        # Check if challenge exists for this week
        response = supabase.table("weekly_challenges").select("*").eq("week_number", week_number).eq("year", year).execute()
        
        if response.data and len(response.data) > 0:
            challenge = response.data[0]
            return {
                "week_number": challenge["week_number"],
                "year": challenge["year"],
                "theme": challenge["theme"],
                "career_path": challenge["career_path"],
                "questions": challenge.get("questions", []),
                "starts_at": challenge["starts_at"],
                "ends_at": challenge["ends_at"]
            }
        
        # Create new challenge for this week
        new_challenge = {
            "week_number": week_number,
            "year": year,
            "theme": "Data Structures & Algorithms",
            "career_path": "General Software Engineer",
            "questions": [],
            "starts_at": week_start.isoformat(),
            "ends_at": week_end.isoformat()
        }
        
        insert_response = supabase.table("weekly_challenges").insert(new_challenge).execute()
        
        if not insert_response.data:
            raise HTTPException(status_code=500, detail="Failed to create weekly challenge")
        
        return {
            "week_number": week_number,
            "year": year,
            "theme": "Data Structures & Algorithms",
            "career_path": "General Software Engineer",
            "questions": [],
            "starts_at": week_start.isoformat(),
            "ends_at": week_end.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching weekly challenge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit")
async def submit_weekly_challenge(request: SubmitWeeklyChallengeRequest):
    """
    Submit weekly challenge result.
    Request: { user_id, score, answers }
    Returns: { success, rank, leaderboard }
    """
    try:
        week_number, year, _, _ = get_current_week_info()
        
        # Get user info
        user_email = "Anonymous"
        try:
            user_response = supabase.table("users").select("email").eq("id", request.user_id).execute()
            if user_response.data:
                user_email = user_response.data[0].get("email", "Anonymous")
        except Exception:
            pass
        
        # Check if user already submitted this week
        existing = supabase.table("weekly_results").select("*").eq("user_id", request.user_id).eq("week_number", week_number).eq("year", year).execute()
        
        if existing.data and len(existing.data) > 0:
            # Update existing score if higher
            if request.score > existing.data[0].get("score", 0):
                supabase.table("weekly_results").update({
                    "score": request.score,
                    "answers": request.answers,
                    "completed_at": datetime.utcnow().isoformat()
                }).eq("id", existing.data[0]["id"]).execute()
        else:
            # Insert new result
            data = {
                "week_number": week_number,
                "year": year,
                "user_id": request.user_id,
                "user_email": user_email,
                "score": request.score,
                "answers": request.answers,
                "completed_at": datetime.utcnow().isoformat()
            }
            supabase.table("weekly_results").insert(data).execute()
        
        # Get leaderboard
        leaderboard_response = supabase.table("weekly_results").select(
            "user_email, score, completed_at"
        ).eq("week_number", week_number).eq("year", year).order("score", desc=True).execute()
        
        leaderboard = []
        user_rank = None
        for i, row in enumerate(leaderboard_response.data):
            entry = {
                "rank": i + 1,
                "user_email": row.get("user_email", "Anonymous"),
                "score": row.get("score", 0),
                "completed_at": row.get("completed_at", "")
            }
            leaderboard.append(entry)
            
            if row.get("user_id") == request.user_id or row.get("user_email") == user_email:
                user_rank = i + 1
        
        return {
            "success": True,
            "rank": user_rank,
            "leaderboard": leaderboard[:10]  # Top 10
        }
    
    except Exception as e:
        print(f"Error submitting weekly challenge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard")
async def get_weekly_leaderboard():
    """
    Get top 10 leaderboard for current week.
    Returns: [{ user_email, score, completed_at, rank }]
    """
    try:
        week_number, year, _, _ = get_current_week_info()
        
        response = supabase.table("weekly_results").select(
            "user_email, score, completed_at"
        ).eq("week_number", week_number).eq("year", year).order("score", desc=True).limit(10).execute()
        
        leaderboard = []
        for i, row in enumerate(response.data):
            leaderboard.append({
                "rank": i + 1,
                "user_email": row.get("user_email", "Anonymous"),
                "score": row.get("score", 0),
                "completed_at": row.get("completed_at", "")
            })
        
        return leaderboard
    
    except Exception as e:
        print(f"Error fetching weekly leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_weekly_challenge(request: StartChallengeRequest):
    """
    Start a weekly challenge attempt.
    Creates a new attempt record if one doesn't exist for this user/week/year.
    Request: { user_id, week_number, year }
    Returns: { success, attempt_id, status }
    """
    try:
        # Check if attempt already exists
        existing = supabase.table("challenge_attempts").select("*").eq("user_id", request.user_id).eq("week_number", request.week_number).eq("year", request.year).execute()
        
        if existing.data and len(existing.data) > 0:
            # Return existing attempt
            return {
                "success": True,
                "attempt_id": existing.data[0]["id"],
                "status": existing.data[0]["status"]
            }
        
        # Create new attempt
        new_attempt = {
            "user_id": request.user_id,
            "week_number": request.week_number,
            "year": request.year,
            "status": "started",
            "started_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        insert_response = supabase.table("challenge_attempts").insert(new_attempt).execute()
        
        if not insert_response.data:
            raise HTTPException(status_code=500, detail="Failed to create challenge attempt")
        
        return {
            "success": True,
            "attempt_id": insert_response.data[0]["id"],
            "status": "started"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error starting weekly challenge: {e}")
        raise HTTPException(status_code=500, detail=str(e))