"""
Badge Service
Handles automatic badge checking and awarding based on user events.
Called internally by backend endpoints (no frontend dependency).
"""
import os
import logging
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)

# Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)


# =============================================================================
# BADGE DEFINITIONS
# Includes XP rewards for each badge
# =============================================================================

BADGES = {
    # Activity-based badges
    "first_session": {
        "id": "first_session",
        "name": "First Step",
        "emoji": "🎯",
        "description": "Complete your first interview session",
        "xp_reward": 10,
        "rarity": "common"
    },
    "sessions_10": {
        "id": "sessions_10",
        "name": "Dedicated",
        "emoji": "💼",
        "description": "Complete 10 interview sessions",
        "xp_reward": 25,
        "rarity": "common"
    },
    "sessions_50": {
        "id": "sessions_50",
        "name": "Interview Master",
        "emoji": "🚀",
        "description": "Complete 50 interview sessions",
        "xp_reward": 75,
        "rarity": "rare"
    },
    
    # Performance badges
    "perfect_score": {
        "id": "perfect_score",
        "name": "Perfect Score",
        "emoji": "💯",
        "description": "Score 50/50 in any session",
        "xp_reward": 50,
        "rarity": "rare"
    },
    
    # Streak badges
    "streak_7": {
        "id": "streak_7",
        "name": "Week Warrior",
        "emoji": "🔥",
        "description": "Maintain a 7 day streak",
        "xp_reward": 50,
        "rarity": "common"
    },
    "streak_30": {
        "id": "streak_30",
        "name": "Monthly Legend",
        "emoji": "🏆",
        "description": "Maintain a 30 day streak",
        "xp_reward": 200,
        "rarity": "legendary"
    },
    
    # Mode-specific badges
    "hard_mode": {
        "id": "hard_mode",
        "name": "Hard Mode Hero",
        "emoji": "😈",
        "description": "Complete a Hard difficulty session",
        "xp_reward": 50,
        "rarity": "rare"
    },
    "simulation": {
        "id": "simulation",
        "name": "Under Pressure",
        "emoji": "⏱️",
        "description": "Complete a Simulation Mode session",
        "xp_reward": 30,
        "rarity": "uncommon"
    },
    "voice_user": {
        "id": "voice_user",
        "name": "Voice Pro",
        "emoji": "🎙️",
        "description": "Answer questions using voice input",
        "xp_reward": 30,
        "rarity": "uncommon"
    },
    
    # Level badge
    "level_5": {
        "id": "level_5",
        "name": "Senior Achiever",
        "emoji": "⚡",
        "description": "Reach Level 5 (Senior)",
        "xp_reward": 100,
        "rarity": "rare"
    },
    
    # Challenge badges
    "challenger": {
        "id": "challenger",
        "name": "Challenger",
        "emoji": "🤜",
        "description": "Challenge a friend",
        "xp_reward": 20,
        "rarity": "common"
    },
    "weekly_winner": {
        "id": "weekly_winner",
        "name": "Weekly Champion",
        "emoji": "🥇",
        "description": "Finish #1 in weekly challenge",
        "xp_reward": 200,
        "rarity": "legendary"
    }
}


def get_user_earned_badges(user_id: str) -> set:
    """Get set of badge_ids user already has."""
    try:
        response = supabase.table("user_badges").select("badge_id").eq("user_id", user_id).execute()
        if response.data:
            return {b.get("badge_id") for b in response.data}
        return set()
    except Exception as e:
        logger.error(f"Error fetching user badges: {e}")
        return set()


def get_user_streak_data(user_id: str) -> dict:
    """Get user's streak data."""
    try:
        response = supabase.table("user_streaks").select("*").eq("user_id", user_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_sessions": 0
        }
    except Exception as e:
        logger.error(f"Error fetching streak data: {e}")
        return {"current_streak": 0, "longest_streak": 0, "total_sessions": 0}


def get_user_rank_data(user_id: str) -> dict:
    """Get user's rank/level data."""
    try:
        response = supabase.table("user_ranks").select("*").eq("user_id", user_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return {"xp": 0, "level": 1}
    except Exception as e:
        logger.error(f"Error fetching rank data: {e}")
        return {"xp": 0, "level": 1}


def get_challenges_created_count(user_id: str) -> int:
    """Get number of challenges created by user."""
    try:
        response = supabase.table("challenges").select("id").eq("creator_id", user_id).execute()
        return len(response.data) if response.data else 0
    except Exception as e:
        logger.error(f"Error fetching challenges count: {e}")
        return 0


def award_badge(user_id: str, badge_id: str) -> dict | None:
    """Award a badge to user. Returns badge info if successful, None if duplicate."""
    try:
        # Insert badge (DB unique constraint prevents duplicates)
        supabase.table("user_badges").insert({
            "user_id": user_id,
            "badge_id": badge_id,
            "earned_at": datetime.utcnow().isoformat()
        }).execute()
        
        # Return badge info
        return BADGES.get(badge_id)
    except Exception as e:
        # Check if it's a duplicate error (unique constraint violation)
        error_str = str(e).lower()
        if "unique" in error_str or "duplicate" in error_str:
            # Badge already exists, this is expected for concurrent calls
            return None
        logger.error(f"Error awarding badge {badge_id}: {e}")
        return None


def add_xp_to_user(user_id: str, xp_amount: int) -> dict:
    """Add XP to user and return updated rank info."""
    try:
        # Get current rank data
        rank_data = get_user_rank_data(user_id)
        current_xp = rank_data.get("xp", 0)
        new_xp = current_xp + xp_amount
        
        # Determine new level based on XP
        new_level = calculate_level(new_xp)
        new_title = calculate_title(new_level)
        
        # Update or insert rank
        if rank_data.get("xp", 0) > 0:
            supabase.table("user_ranks").update({
                "xp": new_xp,
                "level": new_level,
                "rank_title": new_title,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
        else:
            supabase.table("user_ranks").insert({
                "user_id": user_id,
                "xp": new_xp,
                "level": new_level,
                "rank_title": new_title
            }).execute()
        
        return {
            "xp": new_xp,
            "level": new_level,
            "rank_title": new_title,
            "xp_earned": xp_amount
        }
    except Exception as e:
        logger.error(f"Error adding XP: {e}")
        return {"xp": 0, "level": 1, "xp_earned": 0}


def calculate_level(xp: int) -> int:
    """Calculate level from XP."""
    if xp >= 2000:
        return 7
    elif xp >= 1400:
        return 6
    elif xp >= 900:
        return 5
    elif xp >= 500:
        return 4
    elif xp >= 250:
        return 3
    elif xp >= 100:
        return 2
    else:
        return 1


def calculate_title(level: int) -> str:
    """Get title for level."""
    titles = {
        1: "🌱 Fresher",
        2: "📚 Beginner",
        3: "💼 Junior",
        4: "⚡ Mid-level",
        5: "🚀 Senior",
        6: "👑 Principal",
        7: "🏆 Legend"
    }
    return titles.get(level, "🌱 Fresher")


# =============================================================================
# MAIN BADGE CHECK FUNCTION
# Called by endpoints after relevant actions
# =============================================================================

def check_and_award_badges(user_id: str, event: str, event_data: dict = None) -> dict:
    """
    Check which badges user qualifies for and award them.
    
    Args:
        user_id: The user's ID
        event: The event type that triggered the check
               Options: "session_complete", "perfect_score", "hard_mode", 
                        "simulation", "voice_used", "challenge_created",
                        "challenge_won", "streak_milestone"
        event_data: Optional additional data about the event
                   (e.g., {"score": 50, "difficulty": "hard"})
    
    Returns:
        {
            "new_badges": [...],  # List of newly awarded badges
            "total_xp_earned": int,
            "rank_update": {...}  # Updated rank info if XP was added
        }
    """
    try:
        # Get user's current state
        earned_badges = get_user_earned_badges(user_id)
        streak_data = get_user_streak_data(user_id)
        rank_data = get_user_rank_data(user_id)
        
        badges_to_award = []
        total_xp = 0
        
        # Get session count from streak data
        total_sessions = streak_data.get("total_sessions", 0)
        current_streak = streak_data.get("current_streak", 0)
        user_level = rank_data.get("level", 1)
        
        # Get challenges created count
        challenges_count = get_challenges_created_count(user_id)
        
        # =========================================================================
        # SESSION COMPLETE - Check session-based badges
        # =========================================================================
        if event == "session_complete":
            # First session
            if "first_session" not in earned_badges and total_sessions >= 1:
                badges_to_award.append("first_session")
            
            # 10 sessions
            if "sessions_10" not in earned_badges and total_sessions >= 10:
                badges_to_award.append("sessions_10")
            
            # 50 sessions
            if "sessions_50" not in earned_badges and total_sessions >= 50:
                badges_to_award.append("sessions_50")
        
        # =========================================================================
        # PERFECT SCORE - Check score-based badges
        # =========================================================================
        if event == "perfect_score":
            if "perfect_score" not in earned_badges:
                badges_to_award.append("perfect_score")
        
        # =========================================================================
        # HARD MODE - Check difficulty badges
        # =========================================================================
        if event == "hard_mode":
            if "hard_mode" not in earned_badges:
                badges_to_award.append("hard_mode")
        
        # =========================================================================
        # SIMULATION MODE - Check mode badges
        # =========================================================================
        if event == "simulation":
            if "simulation" not in earned_badges:
                badges_to_award.append("simulation")
        
        # =========================================================================
        # VOICE INPUT - Check voice badges
        # =========================================================================
        if event == "voice_used":
            if "voice_user" not in earned_badges:
                badges_to_award.append("voice_user")
        
        # =========================================================================
        # CHALLENGE CREATED - Check challenge creator badges
        # =========================================================================
        if event == "challenge_created":
            if "challenger" not in earned_badges and challenges_count >= 1:
                badges_to_award.append("challenger")
        
        # =========================================================================
        # WEEKLY CHALLENGE WIN - Check challenge winner badges
        # =========================================================================
        if event == "challenge_won":
            if "weekly_winner" not in earned_badges:
                # Check if user got rank 1
                rank = event_data.get("rank", 0) if event_data else 0
                if rank == 1:
                    badges_to_award.append("weekly_winner")
        
        # =========================================================================
        # STREAK MILESTONE - Check streak badges (can be triggered by any session)
        # =========================================================================
        if event in ["session_complete", "streak_milestone"]:
            if "streak_7" not in earned_badges and current_streak >= 7:
                badges_to_award.append("streak_7")
            if "streak_30" not in earned_badges and current_streak >= 30:
                badges_to_award.append("streak_30")
        
        # =========================================================================
        # LEVEL CHECK - Check level-based badges
        # =========================================================================
        if "level_5" not in earned_badges and user_level >= 5:
            badges_to_award.append("level_5")
        
        # =========================================================================
        # AWARD BADGES & XP
        # =========================================================================
        new_badges = []
        for badge_id in badges_to_award:
            badge_info = award_badge(user_id, badge_id)
            if badge_info:
                new_badges.append(badge_info)
                total_xp += badge_info.get("xp_reward", 0)
                logger.info(f"[BADGE] Awarded {badge_id} to user {user_id}")
        
        # Add XP rewards for all new badges
        rank_update = None
        if total_xp > 0:
            rank_update = add_xp_to_user(user_id, total_xp)
            logger.info(f"[XP] Added {total_xp} XP to user {user_id}")
        
        return {
            "new_badges": new_badges,
            "total_xp_earned": total_xp,
            "rank_update": rank_update
        }
        
    except Exception as e:
        logger.error(f"Error in check_and_award_badges: {e}")
        return {
            "new_badges": [],
            "total_xp_earned": 0,
            "rank_update": None
        }


# =============================================================================
# HELPER FUNCTION FOR ENDPOINTS
# Easy way for endpoints to check badges without knowing implementation details
# =============================================================================

def check_badges_on_session_complete(user_id: str, total_score: float = None, difficulty: str = None, is_simulation: bool = False, is_voice: bool = False) -> dict:
    """
    Convenience function to check badges after interview session completion.
    
    Args:
        user_id: User who completed the session
        total_score: Score achieved (for perfect score check)
        difficulty: "easy", "medium", "hard"
        is_simulation: Whether simulation mode was used
        is_voice: Whether voice input was used
    
    Returns:
        Badge check result dict
    """
    events = ["session_complete"]  # Always check session-based badges
    
    # Add event-specific triggers
    if total_score == 50:
        events.append("perfect_score")
    
    if difficulty == "hard":
        events.append("hard_mode")
    
    if is_simulation:
        events.append("simulation")
    
    if is_voice:
        events.append("voice_used")
    
    # Run badge check with all applicable events
    result = check_and_award_badges(user_id, "session_complete")
    
    # Also check perfect score if applicable
    if total_score == 50:
        ps_result = check_and_award_badges(user_id, "perfect_score")
        result["new_badges"].extend(ps_result["new_badges"])
        result["total_xp_earned"] += ps_result["total_xp_earned"]
    
    return result
