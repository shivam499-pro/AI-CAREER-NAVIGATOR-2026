"""
Jobs Router
Unified jobs API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel
from services import job_matching_service, jobs_service
from core.middleware import get_current_user, AuthenticatedUser
from supabase import create_client
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

DEFAULT_PAGE  = 1
DEFAULT_LIMIT = 10
MAX_LIMIT     = 50

# ─── Supabase client ──────────────────────────────────────────────────────────

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


# ─── Request models ───────────────────────────────────────────────────────────

class SaveJobRequest(BaseModel):
    job_id:         str
    title:          str
    company:        str
    location:       Optional[str] = None
    apply_url:      Optional[str] = None
    match_score:    Optional[float] = None
    matched_skills: Optional[List[str]] = []
    missing_skills: Optional[List[str]] = []


class ApplyJobRequest(BaseModel):
    job_id:         str
    title:          str
    company:        str
    location:       Optional[str] = None
    apply_url:      Optional[str] = None
    match_score:    Optional[float] = None
    matched_skills: Optional[List[str]] = []
    missing_skills: Optional[List[str]] = []


# ─── User data helper ─────────────────────────────────────────────────────────

async def get_user_data(user_id: str) -> dict:
    """Fetch user profile and analysis from Supabase."""
    sb = get_supabase()
    user_data = {"profile": None, "analysis": None, "experience_level": "mid"}

    profile_resp = sb.table("profiles").select("*").eq("user_id", user_id).execute()
    if profile_resp.data:
        user_data["profile"] = profile_resp.data[0]

    analysis_resp = sb.table("analyses").select("*").eq("user_id", user_id).execute()
    if analysis_resp.data:
        analysis = analysis_resp.data[0]
        user_data["analysis"] = analysis
        level = (
            analysis.get("experience_level") or
            (analysis.get("analysis") or {}).get("experience_level") or
            "mid"
        )
        user_data["experience_level"] = level

    return user_data


# ─── GET /recommendations ─────────────────────────────────────────────────────

@router.get("/recommendations")
async def get_job_recommendations(
    query:    Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    page:  int = Query(DEFAULT_PAGE,  ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get AI-matched job recommendations based on user profile.
    Falls back to mock data when SerpAPI key is not configured.
    """
    try:
        user_data  = await get_user_data(current_user.user_id)
        jobs_list  = []

        # Try SerpAPI first
        if query:
            try:
                results = await jobs_service.search_jobs(query, location)
                if results:
                    jobs_list = results
            except Exception as e:
                print(f"[Jobs] SerpAPI error: {e}")

        # Fallback mock data
        if not jobs_list:
            jobs_list = _mock_jobs(query, location, job_type)

        # AI matching
        matched = job_matching_service.match_jobs(user_data, jobs_list, limit=20)

        # Paginate
        total       = len(matched)
        total_pages = (total + limit - 1) // limit
        start       = (page - 1) * limit
        paginated   = matched[start : start + limit]

        return {
            "success": True,
            "jobs": paginated,
            "count": len(paginated),
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages
            },
            "match_source": "ai_matching" if user_data["profile"] else "default"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── GET /applications ────────────────────────────────────────────────────────

@router.get("/applications")
async def get_applications(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Return job application status counts for the dashboard pipeline.
    Returns: { status_counts: { applied, interview, rejected, offer } }
    """
    try:
        sb = get_supabase()

        resp = sb.table("job_applications") \
            .select("status") \
            .eq("user_id", current_user.user_id) \
            .execute()

        counts = {"applied": 0, "interview": 0, "rejected": 0, "offer": 0}

        for row in (resp.data or []):
            status = (row.get("status") or "applied").lower()
            if status in counts:
                counts[status] += 1
            else:
                counts["applied"] += 1   # unknown status → applied bucket

        return {
            "success": True,
            "status_counts": counts,
            "total": sum(counts.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── POST /save ───────────────────────────────────────────────────────────────

@router.post("/save")
async def save_job(
    body: SaveJobRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Save a job to the user's saved_jobs list.
    Idempotent — saving the same job twice returns success without duplicating.
    """
    try:
        sb = get_supabase()

        # Check if already saved
        existing = sb.table("saved_jobs") \
            .select("id") \
            .eq("user_id", current_user.user_id) \
            .eq("job_id", body.job_id) \
            .execute()

        if existing.data:
            return {"success": True, "message": "Job already saved", "already_saved": True}

        # Insert
        sb.table("saved_jobs").insert({
            "user_id":        current_user.user_id,
            "job_id":         body.job_id,
            "title":          body.title,
            "company":        body.company,
            "location":       body.location,
            "apply_url":      body.apply_url,
            "match_score":    body.match_score,
            "matched_skills": body.matched_skills,
            "missing_skills": body.missing_skills,
            "saved_at":     datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"success": True, "message": "Job saved successfully", "already_saved": False}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── POST /apply ──────────────────────────────────────────────────────────────

@router.post("/apply")
async def apply_to_job(
    body: ApplyJobRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Record a job application in job_applications table.
    Status starts as 'applied'. User can update to interview/offer/rejected later.
    """
    try:
        sb = get_supabase()

        # Check if already applied
        existing = sb.table("job_applications") \
            .select("id") \
            .eq("user_id", current_user.user_id) \
            .eq("job_id", body.job_id) \
            .execute()

        if existing.data:
            return {
                "success":  True,
                "message":  "Already applied to this job",
                "apply_url": body.apply_url,
                "duplicate": True
            }

        # Insert application record
        sb.table("job_applications").insert({
            "user_id":        current_user.user_id,
            "job_id":         body.job_id,
            "title":          body.title,
            "company":        body.company,
            "location":       body.location,
            "apply_url":      body.apply_url,
            "match_score":    body.match_score,
            "matched_skills": body.matched_skills,
            "missing_skills": body.missing_skills,
            "status":         "applied",
            "applied_at":     datetime.now(timezone.utc).isoformat(),
            "created_at":     datetime.now(timezone.utc).isoformat()
        }).execute()

        return {
            "success":   True,
            "message":   "Application recorded successfully",
            "apply_url": body.apply_url,
            "duplicate": False
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Mock data (fallback when SerpAPI unavailable) ────────────────────────────

def _mock_jobs(
    query:    Optional[str],
    location: Optional[str],
    job_type: Optional[str]
) -> list:
    role = query or "Full Stack Developer"
    jobs = [
        {
            "id":          "mock_1",
            "title":       f"Junior {role}",
            "company":     "Tech Solutions India",
            "location":    "Remote, India",
            "type":        "Full-time",
            "url":         "#",
            "description": "Looking for a developer with Python, React, SQL, git, and REST API experience."
        },
        {
            "id":          "mock_2",
            "title":       role,
            "company":     "Global Dev Center",
            "location":    "Bangalore / Remote",
            "type":        "Full-time",
            "url":         "#",
            "description": "Full stack role requiring JavaScript, TypeScript, Node.js, MongoDB, PostgreSQL, and AWS."
        },
        {
            "id":          "mock_3",
            "title":       f"Intern — {role}",
            "company":     "Innovate Labs",
            "location":    "Chennai, India",
            "type":        "Internship",
            "url":         "#",
            "description": "Internship for CS students. Learn Python, SQL, React, git, and cloud basics."
        },
        {
            "id":          "mock_4",
            "title":       f"Senior {role}",
            "company":     "Tech Corp",
            "location":    "Hyderabad",
            "type":        "Full-time",
            "url":         "#",
            "description": "Senior backend role with Python, FastAPI, PostgreSQL, Docker, Kubernetes, CI/CD, AWS."
        },
        {
            "id":          "mock_5",
            "title":       "Frontend Developer",
            "company":     "Startup India",
            "location":    "Remote",
            "type":        "Full-time",
            "url":         "#",
            "description": "React developer needed. TypeScript, Redux, Tailwind, Jest, REST API experience required."
        }
    ]

    if location:
        jobs = [j for j in jobs if location.lower() in j["location"].lower()]
    if job_type:
        jobs = [j for j in jobs if job_type.lower() in j["type"].lower()]

    return jobs