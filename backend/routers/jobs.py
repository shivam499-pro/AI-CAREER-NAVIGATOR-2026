"""
Jobs Router
Unified jobs API endpoints.

GET /api/jobs/recommendations - Get job recommendations
"""
from fastapi import APIRouter, HTTPException, Header, Depends, Query
from typing import Optional, List
from pydantic import BaseModel
from services import job_matching_service, jobs_service
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 50


async def get_user_from_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Extract user_id from authorization header.
    
    Returns:
        User ID or None if not authenticated
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        return None
    
    async with httpx.AsyncClient() as client:
        try:
            user_resp = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {token}"
                }
            )
            if user_resp.status_code != 200:
                return None
            
            user_info = user_resp.json()
            return user_info.get("id")
        except:
            return None


async def get_user_data(user_id: Optional[str]) -> dict:
    """
    Get user profile and analysis data.
    
    Returns:
        Dict with profile, analysis, experience_level
    """
    if not user_id:
        return {"profile": None, "analysis": None, "experience_level": "mid"}
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        return {"profile": None, "analysis": None, "experience_level": "mid"}
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    
    user_data = {
        "profile": None,
        "analysis": None,
        "experience_level": "mid"
    }
    
    async with httpx.AsyncClient() as client:
        # Fetch profile
        profile_resp = await client.get(
            f"{supabase_url}/rest/v1/profiles?user_id=eq.{user_id}&select=*",
            headers=headers
        )
        if profile_resp.status_code == 200:
            profiles = profile_resp.json()
            if profiles:
                user_data["profile"] = profiles[0]
        
        # Fetch analysis
        analysis_resp = await client.get(
            f"{supabase_url}/rest/v1/analyses?user_id=eq.{user_id}&select=*",
            headers=headers
        )
        if analysis_resp.status_code == 200:
            analyses = analysis_resp.json()
            if analyses:
                analysis = analyses[0]
                user_data["analysis"] = analysis
                if analysis.get("experience_level"):
                    user_data["experience_level"] = analysis["experience_level"]
                elif analysis.get("analysis") and isinstance(analysis["analysis"], dict):
                    user_data["experience_level"] = analysis["analysis"].get("experience_level", "mid")
    
    return user_data


@router.get("/recommendations")
async def get_job_recommendations(
    query: Optional[str] = Query(None, description="Job search query"),
    location: Optional[str] = Query(None, description="Location filter"),
    job_type: Optional[str] = Query(None, description="Job type filter"),
    page: int = Query(DEFAULT_PAGE, ge=1, description="Page number"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Items per page"),
    authorization: Optional[str] = Header(None)
):
    """
    Get job recommendations based on user profile.
    
    Uses AI matching to calculate real match scores.
    """
    try:
        # Get user data
        user_id = await get_user_from_token(authorization)
        user_data = await get_user_data(user_id)
        
        # Search query
        search_query = query
        
        jobs_list = []
        
        if search_query:
            try:
                results = await jobs_service.search_jobs(search_query, location)
                if results and len(results) > 0:
                    jobs_list = results
            except Exception as e:
                print(f"SerpAPI error: {e}")
        
        # Fallback to mock data
        if not jobs_list:
            mock_jobs = [
                {
                    "id": "1",
                    "title": f"Junior {search_query or 'Software Engineer'}",
                    "company": "Tech Solutions India",
                    "location": "Remote, India",
                    "type": "Full-time",
                    "url": "#",
                    "description": "Looking for a Python developer with React experience. Must know SQL and git.",
                },
                {
                    "id": "2",
                    "title": f"{search_query or 'Full Stack Developer'}",
                    "company": "Global Dev Center",
                    "location": "Bangalore / Remote",
                    "type": "Full-time",
                    "url": "#",
                    "description": "Full stack role requiring JavaScript, Node.js, MongoDB, and AWS experience.",
                },
                {
                    "id": "3",
                    "title": f"Intern - {search_query or 'Systems Engineer'}",
                    "company": "Innovate Labs",
                    "location": "Chennai, India",
                    "type": "Internship",
                    "url": "#",
                    "description": "Internship for CS students. Learn Python, SQL, and cloud basics.",
                },
                {
                    "id": "4",
                    "title": f"Senior {search_query or 'Backend Engineer'}",
                    "company": "Tech Corp",
                    "location": "Hyderabad",
                    "type": "Full-time",
                    "url": "#",
                    "description": "Senior backend role with Python, FastAPI, PostgreSQL, Docker, Kubernetes.",
                },
                {
                    "id": "5",
                    "title": "Frontend Developer",
                    "company": "Startup India",
                    "location": "Remote",
                    "type": "Full-time",
                    "url": "#",
                    "description": "React developer needed. Experience with TypeScript, Redux, and CSS.",
                }
            ]
            
            # Apply filters
            if location:
                mock_jobs = [j for j in mock_jobs if location.lower() in j["location"].lower()]
            if job_type:
                mock_jobs = [j for j in mock_jobs if job_type.lower() in j["type"].lower()]
            
            jobs_list = mock_jobs
        
        # Apply AI matching
        matched_jobs = job_matching_service.match_jobs(user_data, jobs_list, limit=20)
        
        # Paginate
        total = len(matched_jobs)
        total_pages = (total + limit - 1) // limit
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        paginated_jobs = matched_jobs[start_idx:end_idx]
        
        return {
            "success": True,
            "jobs": paginated_jobs,
            "count": len(paginated_jobs),
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
