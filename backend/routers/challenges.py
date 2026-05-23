from fastapi import APIRouter, HTTPException, Query, Depends
from core.supabase_client import supabase
from core.middleware import get_current_user, AuthenticatedUser
from pydantic import BaseModel
from supabase import create_client, Client
import os
import random
import string
import traceback
from datetime import datetime

router = APIRouter()


class CreateChallengeRequest(BaseModel):
    career_path: str
    questions: list


class SubmitChallengeRequest(BaseModel):
    challenge_code: str
    score: float
    answers: list


def generate_challenge_code(length: int = 8) -> str:
    """Generate a random 8-character challenge code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


@router.post("/create")
async def create_challenge(request: CreateChallengeRequest,
                           current_user: AuthenticatedUser = Depends(get_current_user)):
    try:
        # Generate unique challenge code
        challenge_code = generate_challenge_code()
        
        # Check if code already exists (very unlikely but handle it)
        existing = supabase.table("challenges").select("challenge_code").eq("challenge_code", challenge_code).execute()
        while existing.data:
            challenge_code = generate_challenge_code()
            existing = supabase.table("challenges").select("challenge_code").eq("challenge_code", challenge_code).execute()
        
        # Get creator name
        creator_name = "Anonymous"
        try:
            user_response = supabase.table("profiles").select("full_name, email").eq("id", current_user.user_id).execute()
            if user_response.data and user_response.data[0].get("full_name"):
                creator_name = user_response.data[0]["full_name"]
            elif user_response.data and user_response.data[0].get("email"):
                creator_name = user_response.data[0]["email"].split("@")[0]
        except Exception:
            pass
        
        # Insert challenge into database
        data = {
            "challenge_code": challenge_code,
            "creator_id": current_user.user_id,
            "career_path": request.career_path,
            "questions": request.questions
        }
        
        response = supabase.table("challenges").insert(data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create challenge")
        
        base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        share_url = f"{base_url}/challenge/{challenge_code}"
        return {
            "challenge_code": challenge_code,
            "share_url": share_url,
            "creator_name": creator_name
        }
    
    except Exception as e:
        print(f"Challenge create error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{challenge_code}")
async def get_challenge(challenge_code: str):
    """
    Get challenge details by code.
    Returns: { challenge_code, career_path, questions, creator_name }
    """
    try:
        response = supabase.table("challenges").select("*").eq("challenge_code", challenge_code.upper()).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        challenge = response.data[0]
        
        return {
            "challenge_code": challenge["challenge_code"],
            "career_path": challenge["career_path"],
            "questions": challenge["questions"],
            "creator_name": challenge.get("creator_name", "Anonymous")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching challenge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit")
async def submit_challenge_result(request: SubmitChallengeRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Submit challenge result.
    Request: { challenge_code, user_id, score, answers }
    Returns: { success, leaderboard }
    """
    try:
        # Get user info
        user_email = "Anonymous"
        user_name = "Anonymous"
        try:
            user_response = supabase.table("profiles").select("full_name, email").eq("id", current_user.user_id).execute()
            if user_response.data:
                user_name = user_response.data[0].get("full_name") or user_response.data[0].get("email", "Anonymous").split("@")[0]
                user_email = user_response.data[0].get("email", "Anonymous")
        except Exception:
            pass
        
        # Insert result
        data = {
            "challenge_code": request.challenge_code.upper(),
            "user_id": current_user.user_id,
            "user_email": user_email,
            "user_name": user_name,
            "score": request.score,
            "answers": request.answers,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("challenge_results").insert(data).execute()
        
        # Get leaderboard
        leaderboard_response = supabase.table("challenge_results").select(
            "user_name, user_email, score, completed_at"
        ).eq("challenge_code", request.challenge_code.upper()).order("score", desc=True).execute()
        
        leaderboard = []
        for i, row in enumerate(leaderboard_response.data):
            leaderboard.append({
                "rank": i + 1,
                "user_name": row.get("user_name", "Anonymous"),
                "user_email": row.get("user_email", ""),
                "score": row.get("score", 0),
                "completed_at": row.get("completed_at", "")
            })
        
        return {
            "success": True,
            "leaderboard": leaderboard
        }
    
    except Exception as e:
        print(f"Error submitting challenge result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard/{challenge_code}")
async def get_leaderboard(
    challenge_code: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page")
):
    """
    Get leaderboard for a challenge with pagination.
    Returns paginated leaderboard with metadata.
    """
    try:
        # First get total count
        count_response = supabase.table("challenge_results").select(
            "user_name, user_email, score, completed_at",
            count=True
        ).eq("challenge_code", challenge_code.upper()).execute()
        
        total = count_response.count or 0
        total_pages = (total + limit - 1) // limit
        
        # Get paginated results
        response = supabase.table("challenge_results").select(
            "user_name, user_email, score, completed_at"
        ).eq("challenge_code", challenge_code.upper()).order("score", desc=True).range(
            (page - 1) * limit,
            page * limit - 1
        ).execute()
        
        leaderboard = []
        for i, row in enumerate(response.data):
            leaderboard.append({
                "rank": (page - 1) * limit + i + 1,
                "user_name": row.get("user_name", "Anonymous"),
                "user_email": row.get("user_email", ""),
                "score": row.get("score", 0),
                "completed_at": row.get("completed_at", "")
            })
        
        return {
            "leaderboard": leaderboard,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages
            }
        }
    
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))