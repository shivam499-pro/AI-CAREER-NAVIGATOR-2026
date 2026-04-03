"""
Challenges Router
Handles challenge links for friends to compete in interviews
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client
import os
import random
import string
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)


def generate_challenge_code(length=8):
    """Generate a random challenge code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


class CreateChallengeRequest(BaseModel):
    user_id: str
    career_path: str
    questions: list


class SubmitChallengeRequest(BaseModel):
    challenge_code: str
    user_id: str
    score: float
    answers: list


@router.post("/create")
async def create_challenge(body: CreateChallengeRequest):
    """
    Create a new challenge and return shareable link
    """
    try:
        # Generate unique challenge code
        challenge_code = generate_challenge_code()
        
        # Make sure code is unique
        while True:
            existing = supabase.table("challenges").select("challenge_code").eq("challenge_code", challenge_code).execute()
            if not existing.data:
                break
            challenge_code = generate_challenge_code()
        
        # Save challenge to database
        supabase.table("challenges").insert({
            "challenge_code": challenge_code,
            "creator_id": body.user_id,
            "career_path": body.career_path,
            "questions": body.questions
        }).execute()
        
        # Get share URL (use the frontend URL)
        frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")
        share_url = f"{frontend_url}/challenge/{challenge_code}"
        
        return {
            "challenge_code": challenge_code,
            "share_url": share_url
        }
        
    except Exception as e:
        print(f"Error creating challenge: {e}")
        raise HTTPException(status_code=500, detail="Failed to create challenge")


@router.get("/{challenge_code}")
async def get_challenge(challenge_code: str):
    """
    Fetch challenge details by code
    """
    try:
        # Fetch challenge
        response = supabase.table("challenges").select("*").eq("challenge_code", challenge_code.upper()).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        challenge = response.data[0]
        
        # Get creator name
        creator_name = "Friend"
        if challenge.get("creator_id"):
            user_response = supabase.table("users").select("full_name, email").eq("id", challenge["creator_id"]).execute()
            if user_response.data and len(user_response.data) > 0:
                user = user_response.data[0]
                creator_name = user.get("full_name") or user.get("email") or "Friend"
        
        return {
            "challenge_code": challenge["challenge_code"],
            "career_path": challenge["career_path"],
            "questions": challenge["questions"],
            "creator_name": creator_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching challenge: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch challenge")


@router.post("/submit")
async def submit_challenge(body: SubmitChallengeRequest):
    """
    Submit challenge result and return leaderboard
    """
    try:
        # Save result
        supabase.table("challenge_results").insert({
            "challenge_code": body.challenge_code.upper(),
            "user_id": body.user_id,
            "score": body.score,
            "answers": body.answers
        }).execute()
        
        # Get leaderboard
        leaderboard = await get_leaderboard(body.challenge_code)
        
        return {
            "success": True,
            "leaderboard": leaderboard
        }
        
    except Exception as e:
        print(f"Error submitting challenge: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit challenge")


@router.get("/leaderboard/{challenge_code}")
async def get_leaderboard(challenge_code: str):
    """
    Get all results for a challenge sorted by score
    """
    try:
        response = supabase.table("challenge_results").select("*").eq("challenge_code", challenge_code.upper()).order("score", desc=True).execute()
        
        leaderboard = []
        for i, result in enumerate(response.data if response.data else []):
            # Get user info
            user_name = f"Player {i + 1}"
            if result.get("user_id"):
                user_response = supabase.table("users").select("full_name, email").eq("id", result["user_id"]).execute()
                if user_response.data and len(user_response.data) > 0:
                    user = user_response.data[0]
                    user_name = user.get("full_name") or user.get("email") or f"Player {i + 1}"
            
            leaderboard.append({
                "rank": i + 1,
                "user_name": user_name,
                "score": result.get("score", 0),
                "completed_at": result.get("completed_at")
            })
        
        return leaderboard
        
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return []