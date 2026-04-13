"""
Career Brain Service
Central intelligence layer that aggregates all user data and generates actionable insights.
"""
import httpx
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

load_dotenv()

# In-memory cache (in production, use Redis)
_career_brain_cache: Dict[str, Dict] = {}
_cache_ttl = 600  # 10 minutes


# =============================================================================
# DATA FETCHING FUNCTIONS
# =============================================================================

async def fetch_profile(supabase_url: str, headers: Dict, user_id: str) -> Optional[Dict]:
    """Fetch user profile."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/profiles?user_id=eq.{user_id}&select=*",
            headers=headers
        )
        if resp.status_code == 200:
            data = resp.json()
            return data[0] if data else None
    return None


async def fetch_analysis(supabase_url: str, headers: Dict, user_id: str) -> Optional[Dict]:
    """Fetch career analysis."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/analyses?user_id=eq.{user_id}&select=*",
            headers=headers
        )
        if resp.status_code == 200:
            data = resp.json()
            return data[0] if data else None
    return None


async def fetch_interview_sessions(supabase_url: str, headers: Dict, user_id: str, limit: int = 20) -> List[Dict]:
    """Fetch recent interview sessions."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/interview_sessions?user_id=eq.{user_id}&order=created_at.desc&limit={limit}",
            headers=headers
        )
        if resp.status_code == 200:
            return resp.json()
    return []


async def fetch_job_applications(supabase_url: str, headers: Dict, user_id: str, limit: int = 50) -> List[Dict]:
    """Fetch job applications."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/job_applications?user_id=eq.{user_id}&order=applied_at.desc&limit={limit}",
            headers=headers
        )
        if resp.status_code == 200:
            return resp.json()
    return []


async def fetch_saved_jobs(supabase_url: str, headers: Dict, user_id: str, limit: int = 20) -> List[Dict]:
    """Fetch saved jobs."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/saved_jobs?user_id=eq.{user_id}&order=saved_at.desc&limit={limit}",
            headers=headers
        )
        if resp.status_code == 200:
            return resp.json()
    return []


async def fetch_user_streak(supabase_url: str, headers: Dict, user_id: str) -> Optional[Dict]:
    """Fetch user streak data."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/user_streaks?user_id=eq.{user_id}&select=*",
            headers=headers
        )
        if resp.status_code == 200:
            data = resp.json()
            return data[0] if data else None
    return None


async def fetch_user_rank(supabase_url: str, headers: Dict, user_id: str) -> Optional[Dict]:
    """Fetch user rank/XP data."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/user_ranks?user_id=eq.{user_id}&select=*",
            headers=headers
        )
        if resp.status_code == 200:
            data = resp.json()
            return data[0] if data else None
    return None


# =============================================================================
# SKILL ANALYSIS
# =============================================================================

def analyze_skills(profile: Optional[Dict], analysis: Optional[Dict], applications: List[Dict]) -> Dict[str, Any]:
    """Analyze user skills and identify patterns."""
    
    strong_skills = []
    weak_skills = []
    missing_skills = []
    
    # Get skills from profile
    if profile:
        tech_stack = profile.get("current_tech_stack", [])
        if isinstance(tech_stack, list):
            strong_skills.extend([s.lower() for s in tech_stack if isinstance(s, str)])
        
        extra_skills = profile.get("extra_skills", [])
        if isinstance(extra_skills, list):
            strong_skills.extend([s.lower() for s in extra_skills if isinstance(s, str)])
    
    # Get skills from analysis
    if analysis:
        strengths = analysis.get("strengths", [])
        if isinstance(strengths, list):
            strong_skills.extend([s.lower() for s in strengths if isinstance(s, str)])
        
        # Get skill gaps
        skill_gaps = analysis.get("skill_gaps", [])
        if isinstance(skill_gaps, list):
            weak_skills.extend([s.lower() for s in skill_gaps if isinstance(s, str)])
        elif isinstance(skill_gaps, dict):
            for v in skill_gaps.values():
                if isinstance(v, list):
                    weak_skills.extend([s.lower() for s in v if isinstance(s, str)])
    
    # Aggregate missing skills from job applications
    all_missing = []
    for app in applications:
        app_missing = app.get("missing_skills", [])
        if isinstance(app_missing, list):
            all_missing.extend([s.lower() for s in app_missing if isinstance(s, str)])
    
    # Count frequency of missing skills
    from collections import Counter
    missing_counter = Counter(all_missing)
    missing_skills = [skill for skill, count in missing_counter.most_common(5)]
    
    # Deduplicate
    strong_skills = list(set(strong_skills))
    weak_skills = list(set(weak_skills))
    
    return {
        "strong": strong_skills[:10],
        "weak": weak_skills[:10],
        "missing": missing_skills[:10]
    }


# =============================================================================
# JOB READINESS SCORE
# =============================================================================

def calculate_job_readiness_score(
    profile: Optional[Dict],
    analysis: Optional[Dict],
    applications: List[Dict],
    interview_sessions: List[Dict]
) -> float:
    """Calculate overall job readiness score (0-100)."""
    
    score = 50  # Base score
    
    # Skill coverage (25 points max)
    if analysis:
        skill_gaps = analysis.get("skill_gaps", [])
        if not skill_gaps:
            score += 25
        elif isinstance(skill_gaps, list):
            gap_penalty = min(20, len(skill_gaps) * 3)
            score += (25 - gap_penalty)
        elif isinstance(skill_gaps, dict):
            gap_count = sum(len(v) for v in skill_gaps.values() if isinstance(v, list))
            gap_penalty = min(20, gap_count * 3)
            score += (25 - gap_penalty)
    
    # Application activity (20 points max)
    if applications:
        applied_count = len([a for a in applications if a.get("status") in ["applied", "interview", "offer"]])
        if applied_count >= 10:
            score += 20
        elif applied_count >= 5:
            score += 15
        elif applied_count >= 1:
            score += 10
    
    # Interview performance (20 points max)
    if interview_sessions:
        total_score = sum(s.get("total_score", 0) for s in interview_sessions)
        avg_score = total_score / len(interview_sessions) if interview_sessions else 0
        if avg_score >= 80:
            score += 20
        elif avg_score >= 60:
            score += 15
        elif avg_score >= 40:
            score += 10
    
    # Profile completeness (15 points max)
    if profile:
        completeness = 0
        if profile.get("current_tech_stack"): completeness += 5
        if profile.get("resume_text"): completeness += 5
        if profile.get("github_username"): completeness += 2.5
        if profile.get("leetcode_username"): completeness += 2.5
        score += completeness
    
    # Analysis completion (10 points max)
    if analysis:
        score += 10
    
    return min(100, max(0, round(score, 1)))


# =============================================================================
# BEHAVIORAL INSIGHTS
# =============================================================================

def generate_behavioral_insights(
    applications: List[Dict],
    interview_sessions: List[Dict],
    streak: Optional[Dict],
    saved_jobs: List[Dict]
) -> List[str]:
    """Generate behavioral insights based on user activity."""
    
    insights = []
    
    # Application patterns
    if len(applications) >= 5:
        rejected = len([a for a in applications if a.get("status") == "rejected"])
        total = len(applications)
        if rejected / total > 0.7:
            insights.append("You've had many rejections. Consider improving your skills before applying to more roles.")
        elif rejected / total < 0.3:
            insights.append("Great application-to-interview conversion rate!")
    
    # Interview practice
    if len(interview_sessions) >= 3:
        scores = [s.get("total_score", 0) for s in interview_sessions]
        if scores[-1] > scores[0]:
            insights.append("Your interview performance is improving over time!")
        elif scores[-1] < scores[0]:
            insights.append("Your interview scores have dropped. Consider more practice.")
    
    # Streak/consistency
    if streak:
        current_streak = streak.get("current_streak", 0)
        if current_streak == 0:
            insights.append("Start your streak today! Consistent practice leads to better outcomes.")
        elif current_streak >= 7:
            insights.append(f"Impressive! {current_streak} day streak. Keep it up!")
    
    # Saved jobs but no applications
    if len(saved_jobs) >= 5 and len(applications) < 3:
        insights.append("You have saved jobs but haven't applied. Time to take action!")
    
    # No activity
    if not applications and not interview_sessions:
        insights.append("Start by exploring jobs or practicing for interviews!")
    
    return insights[:3]


# =============================================================================
# RECOMMENDATION ENGINE
# =============================================================================

def generate_recommendations(
    skill_insights: Dict[str, List[str]],
    job_readiness: float,
    applications: List[Dict],
    missing_skills: List[str],
    weak_skills: List[str]
) -> List[str]:
    """Generate actionable recommendations."""
    
    recommendations = []
    
    # Skill-based recommendations
    if missing_skills:
        top_missing = missing_skills[:3]
        recommendations.append(f"Learn {', '.join(top_missing)} to improve your job match by ~20%")
    
    if weak_skills:
        recommendations.append(f"Practice {weak_skills[0]} through real projects to strengthen your profile")
    
    # Application recommendations
    applied = len([a for a in applications if a.get("status") in ["applied", "interview"]])
    if applied < 3:
        recommendations.append("Apply to at least 5 more jobs this week to increase your chances")
    
    # Interview preparation
    if job_readiness < 60:
        recommendations.append("Practice system design interviews to boost your readiness score")
    
    # If low readiness and no applications
    if job_readiness < 50 and applied == 0:
        recommendations.append("Complete your profile and run analysis to get personalized job recommendations")
    
    # Growth recommendations
    if job_readiness > 80:
        recommendations.append("Your job readiness is high! Focus on interview prep and applying to top companies")
    
    return recommendations[:5]


# =============================================================================
# RISK DETECTION
# =============================================================================

def detect_risks(
    applications: List[Dict],
    interview_sessions: List[Dict],
    streak: Optional[Dict],
    last_activity: Optional[str]
) -> List[str]:
    """Detect potential risks and generate alerts."""
    
    alerts = []
    
    # Rejection streak
    if len(applications) >= 5:
        recent_apps = applications[:5]
        rejected = [a for a in recent_apps if a.get("status") == "rejected"]
        if len(rejected) >= 4:
            alerts.append("⚠️ You have 4+ rejections recently. Consider upskilling before applying more")
    
    # No interview practice
    if interview_sessions:
        latest = interview_sessions[0].get("created_at", "")
        if latest:
            try:
                from datetime import datetime
                last_practice = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                days_since = (datetime.now() - last_practice).days
                if days_since > 14:
                    alerts.append(f"⚠️ No interview practice in {days_since} days. Stay sharp!")
            except:
                pass
    
    # No activity streak
    if streak:
        last_date = streak.get("last_practice_date")
        if last_date:
            try:
                last_practice = datetime.strptime(last_date, "%Y-%m-%d")
                days_since = (datetime.now() - last_practice).days
                if days_since > 7:
                    alerts.append(f"⚠️ No activity in {days_since} days. Start your streak today!")
            except:
                pass
    
    # Low streak
    current = streak.get("current_streak", 0) if streak else 0
    if current < 3 and len(applications) > 0:
        alerts.append("⚠️ Low consistency. Aim for a 7-day streak for better results")
    
    return alerts[:3]


# =============================================================================
# PROGRESS SUMMARY
# =============================================================================

def get_progress_summary(applications: List[Dict], interview_sessions: List[Dict], saved_jobs: List[Dict]) -> Dict[str, int]:
    """Generate progress summary."""
    
    status_counts = {"applied": 0, "interview": 0, "rejected": 0, "offer": 0}
    for app in applications:
        status = app.get("status", "applied")
        if status in status_counts:
            status_counts[status] += 1
    
    return {
        "total_applications": len(applications),
        "total_interviews": status_counts["interview"],
        "total_offers": status_counts["offer"],
        "total_rejections": status_counts["rejected"],
        "saved_jobs": len(saved_jobs),
        "interview_sessions": len(interview_sessions)
    }


# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def get_career_brain(user_id: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Main function to get complete career intelligence.
    
    Returns comprehensive career brain data including:
    - Job readiness score
    - Skill analysis
    - Recommendations
    - Alerts
    - Progress summary
    """
    
    # Check cache
    if use_cache and user_id in _career_brain_cache:
        cached = _career_brain_cache[user_id]
        if "cached_at" in cached:
            import time
            if time.time() - cached["cached_at"] < _cache_ttl:
                return cached
    
    # Get Supabase config
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        return {"error": "Database not configured"}
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    
    # Fetch all data
    profile = await fetch_profile(supabase_url, headers, user_id)
    analysis = await fetch_analysis(supabase_url, headers, user_id)
    applications = await fetch_job_applications(supabase_url, headers, user_id)
    saved_jobs = await fetch_saved_jobs(supabase_url, headers, user_id)
    interview_sessions = await fetch_interview_sessions(supabase_url, headers, user_id)
    streak = await fetch_user_streak(supabase_url, headers, user_id)
    rank = await fetch_user_rank(supabase_url, headers, user_id)
    
    # Process data
    skill_insights = analyze_skills(profile, analysis, applications)
    job_readiness = calculate_job_readiness_score(profile, analysis, applications, interview_sessions)
    insights = generate_behavioral_insights(applications, interview_sessions, streak, saved_jobs)
    recommendations = generate_recommendations(
        skill_insights,
        job_readiness,
        applications,
        skill_insights.get("missing", []),
        skill_insights.get("weak", [])
    )
    alerts = detect_risks(applications, interview_sessions, streak, None)
    progress = get_progress_summary(applications, interview_sessions, saved_jobs)
    
    # Build response
    result = {
        "job_readiness_score": job_readiness,
        "skill_insights": skill_insights,
        "behavioral_insights": insights,
        "recommendations": recommendations,
        "alerts": alerts,
        "progress_summary": progress,
        "streak": streak.get("current_streak", 0) if streak else 0,
        "rank": rank.get("rank_title", "Newcomer") if rank else "Newcomer",
        "level": rank.get("level", 1) if rank else 1,
        "xp": rank.get("xp", 0) if rank else 0
    }
    
    # Cache result
    import time
    result["cached_at"] = time.time()
    _career_brain_cache[user_id] = result
    
    return result


def clear_cache(user_id: str = None):
    """Clear cache for a specific user or all users."""
    global _career_brain_cache
    if user_id:
        _career_brain_cache.pop(user_id, None)
    else:
        _career_brain_cache = {}