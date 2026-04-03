"""
Badges Router
Handles user achievement badges system
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)


# Badge definitions (hardcoded list)
BADGES = [
    {"id": "first_session", "name": "First Step", "emoji": "🎯", 
     "description": "Complete your first interview session"},
    {"id": "perfect_score", "name": "Perfect Score", "emoji": "💯", 
     "description": "Score 50/50 in any session"},
    {"id": "streak_7", "name": "Week Warrior", "emoji": "🔥", 
     "description": "Maintain a 7 day streak"},
    {"id": "streak_30", "name": "Monthly Legend", "emoji": "🏆", 
     "description": "Maintain a 30 day streak"},
    {"id": "sessions_10", "name": "Dedicated", "emoji": "💼", 
     "description": "Complete 10 interview sessions"},
    {"id": "sessions_50", "name": "Interview Master", "emoji": "🚀", 
     "description": "Complete 50 interview sessions"},
    {"id": "hard_mode", "name": "Hard Mode Hero", "emoji": "😈", 
     "description": "Complete a Hard difficulty session"},
    {"id": "simulation", "name": "Under Pressure", "emoji": "⏱️", 
     "description": "Complete a Simulation Mode session"},
    {"id": "voice_user", "name": "Voice Pro", "emoji": "🎙️", 
     "description": "Answer 5 questions using voice input"},
    {"id": "level_5", "name": "Senior Achiever", "emoji": "⚡", 
     "description": "Reach Level 5 (Senior)"},
    {"id": "challenger", "name": "Challenger", "emoji": "🤜", 
     "description": "Challenge a friend"},
    {"id": "weekly_winner", "name": "Weekly Champion", "emoji": "🥇", 
     "description": "Finish #1 in weekly challenge"}
]


class CheckBadgeRequest(BaseModel):
    user_id: str
    event: str


@router.get("/{user_id}")
async def get_user_badges(user_id: str):
    """
    Fetch user's earned badges from "user_badges" table
    Returns: { earned: [...badges], all_badges: [...BADGES] }
    """
    try:
        # Get user's earned badges
        response = supabase.table("user_badges").select("*").eq("user_id", user_id).execute()
        
        earned_badges = []
        if response.data:
            for badge_record in response.data:
                badge_id = badge_record.get("badge_id")
                # Find badge definition
                for badge in BADGES:
                    if badge["id"] == badge_id:
                        earned_badges.append({
                            "badge_id": badge_id,
                            "name": badge["name"],
                            "emoji": badge["emoji"],
                            "description": badge["description"],
                            "earned_at": badge_record.get("earned_at")
                        })
                        break
        
        return {
            "earned": earned_badges,
            "all_badges": BADGES
        }
        
    except Exception as e:
        print(f"Error fetching badges: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch badges")


@router.post("/check")
async def check_and_award_badges(request: CheckBadgeRequest):
    """
    Check which badges user qualifies for based on event
    Events: "session_complete", "perfect_score", "hard_mode", "simulation", "voice_used", "challenge_created"
    Cross check with user_streaks, user_ranks tables
    Award any new badges by inserting to "user_badges" table
    Returns: { newly_earned: [...badges] }
    """
    try:
        user_id = request.user_id
        event = request.event
        newly_earned = []
        
        # Get current badges to avoid duplicates
        existing_response = supabase.table("user_badges").select("badge_id").eq("user_id", user_id).execute()
        existing_badges = set()
        if existing_response.data:
            existing_badges = {b.get("badge_id") for b in existing_response.data}
        
        # Get streak data
        streak_response = supabase.table("user_streaks").select("*").eq("user_id", user_id).execute()
        streak_data = streak_response.data[0] if streak_response.data else None
        
        # Get rank data
        rank_response = supabase.table("user_ranks").select("*").eq("user_id", user_id).execute()
        rank_data = rank_response.data[0] if rank_response.data else None
        
        # Get challenges created count
        challenges_response = supabase.table("challenges").select("id").eq("creator_id", user_id).execute()
        challenges_count = len(challenges_response.data) if challenges_response.data else 0
        
        # Get voice usage count - check interview sessions with voice
        # We'll track voice_answers in a separate table or use an aggregate
        voice_count_response = supabase.table("user_voice_answers").select("count").eq("user_id", user_id).execute()
        voice_count = 0
        if voice_count_response.data:
            voice_count = sum(v.get("count", 0) for v in voice_count_response.data)
        
        # Define badge checks based on event
        badges_to_check = []
        
        if event == "session_complete":
            total_sessions = streak_data.get("total_sessions", 0) if streak_data else 0
            if total_sessions >= 1:
                badges_to_check.append("first_session")
            if total_sessions >= 10:
                badges_to_check.append("sessions_10")
            if total_sessions >= 50:
                badges_to_check.append("sessions_50")
                
        elif event == "perfect_score":
            badges_to_check.append("perfect_score")
            
        elif event == "hard_mode":
            badges_to_check.append("hard_mode")
            
        elif event == "simulation":
            badges_to_check.append("simulation")
            
        elif event == "voice_used":
            # Increment voice count - this is called each time voice is used
            # We need to track total voice answers across all sessions
            voice_count += 1
            if voice_count >= 5:
                badges_to_check.append("voice_user")
                
        elif event == "challenge_created":
            if challenges_count >= 1:
                badges_to_check.append("challenger")
        
        # Check streak badges (can be triggered by any event)
        if streak_data:
            current_streak = streak_data.get("current_streak", 0)
            if current_streak >= 7:
                badges_to_check.append("streak_7")
            if current_streak >= 30:
                badges_to_check.append("streak_30")
        
        # Check level badge
        if rank_data:
            level = rank_data.get("level", 0)
            if level >= 5:
                badges_to_check.append("level_5")
        
        # Award new badges
        for badge_id in badges_to_check:
            if badge_id not in existing_badges:
                # Find badge definition
                badge_def = next((b for b in BADGES if b["id"] == badge_id), None)
                if badge_def:
                    # Insert into user_badges
                    supabase.table("user_badges").insert({
                        "user_id": user_id,
                        "badge_id": badge_id,
                        "earned_at": datetime.utcnow().isoformat()
                    }).execute()
                    
                    newly_earned.append({
                        "badge_id": badge_id,
                        "name": badge_def["name"],
                        "emoji": badge_def["emoji"],
                        "description": badge_def["description"]
                    })
                    existing_badges.add(badge_id)
        
        return {"newly_earned": newly_earned}
        
    except Exception as e:
        print(f"Error checking badges: {e}")
        raise HTTPException(status_code=500, detail="Failed to check badges")


# # Supabase table (as comment):
# -- CREATE TABLE user_badges (
# --   id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
# --   user_id uuid REFERENCES auth.users(id),
# --   badge_id text NOT NULL,
# --   earned_at timestamp DEFAULT now(),
# --   UNIQUE(user_id, badge_id)
# -- );