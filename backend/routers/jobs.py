from fastapi import APIRouter, HTTPException, Query, Header, Body
from typing import Optional, List
from pydantic import BaseModel
from services import jobs_service
from services import job_matching_service
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Default pagination settings
DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 50

# Pydantic models for request bodies
class SaveJobRequest(BaseModel):
    job_id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    apply_url: Optional[str] = None
    match_score: Optional[float] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None

class ApplyJobRequest(BaseModel):
    job_id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    apply_url: Optional[str] = None
    match_score: Optional[float] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None

class UpdateApplicationRequest(BaseModel):
    status: str
    notes: Optional[str] = None


def paginate_response(data: list, page: int, limit: int) -> dict:
    """Add pagination metadata to a list response."""
    total = len(data)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    
    return {
        "data": data[start_idx:end_idx],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages
        }
    }


async def get_user_data_from_supabase(user_id: str) -> dict:
    """
    Fetch user profile and analysis data from Supabase.
    """
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
                # Get experience level from analysis
                if analysis.get("experience_level"):
                    user_data["experience_level"] = analysis["experience_level"]
                elif analysis.get("analysis") and isinstance(analysis["analysis"], dict):
                    user_data["experience_level"] = analysis["analysis"].get("experience_level", "mid")
    
    return user_data


@router.get("/")
async def get_jobs(
    query: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    keywords: Optional[str] = Query(None),
    page: int = Query(DEFAULT_PAGE, ge=1, description="Page number"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Items per page"),
    authorization: Optional[str] = Header(None)
):
    """
    Get job suggestions based on user profile and filters.
    Supports pagination with page and limit query parameters.
    Uses AI matching to calculate real match scores based on user skills.
    """
    try:
        # Extract user_id from authorization header if available
        user_id = None
        user_data = {"profile": None, "analysis": None, "experience_level": "mid"}
        
        if authorization and authorization.startswith("Bearer "):
            # Try to get user from Supabase
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
            
            if supabase_url and supabase_key:
                token = authorization.replace("Bearer ", "")
                async with httpx.AsyncClient() as client:
                    user_resp = await client.get(
                        f"{supabase_url}/auth/v1/user",
                        headers={
                            "apikey": supabase_key,
                            "Authorization": f"Bearer {token}"
                        }
                    )
                    if user_resp.status_code == 200:
                        user_info = user_resp.json()
                        user_id = user_info.get("id")
                        if user_id:
                            user_data = await get_user_data_from_supabase(user_id)
        
        # Use the query provided or fallback to keywords/mock
        search_query = query or keywords
        
        jobs_list = []
        
        if search_query:
            # Try to fetch real jobs from SerpAPI
            try:
                results = await jobs_service.search_jobs(search_query, location)
                if results and len(results) > 0:
                    jobs_list = results
            except Exception as e:
                print(f"SerpAPI error: {e}")
                # Fall through to mock data
        
        # Fallback to mock job data if no jobs found
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
                    "title": f"Frontend Developer",
                    "company": "Startup India",
                    "location": "Remote",
                    "type": "Full-time",
                    "url": "#",
                    "description": "React developer needed. Experience with TypeScript, Redux, and CSS.",
                }
            ]
            
            # Apply filters to mock data
            if location:
                mock_jobs = [j for j in mock_jobs if location.lower() in j["location"].lower()]
            if job_type:
                mock_jobs = [j for j in mock_jobs if job_type.lower() in j["type"].lower()]
            
            jobs_list = mock_jobs
        
        # Apply AI matching to calculate real match scores
        matched_jobs = job_matching_service.match_jobs(user_data, jobs_list, limit=20)
        
        # Paginate results
        paginated = paginate_response(matched_jobs, page, limit)
        
        return {
            "jobs": paginated["data"],
            "count": len(paginated["data"]),
            "pagination": paginated["pagination"],
            "match_source": "ai_matching" if user_data["profile"] else "default"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_jobs(
    query: str = Query(...),
    location: Optional[str] = Query(None)
):
    """
    Search for jobs using external APIs.
    """
    try:
        # In production, use SerpAPI or similar
        results = await jobs_service.search_jobs(query, location)
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SAVED JOBS ENDPOINTS
# =============================================================================

async def get_supabase_client(authorization: str = None):
    """Get Supabase client with proper auth."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        return None, None, None
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        async with httpx.AsyncClient() as client:
            user_resp = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={"apikey": supabase_key, "Authorization": f"Bearer {token}"}
            )
            if user_resp.status_code == 200:
                user_info = user_resp.json()
                user_id = user_info.get("id")
                # Use user's token for RLS
                headers["Authorization"] = f"Bearer {token}"
    
    return supabase_url, headers, user_id


@router.post("/save")
async def save_job(
    job: SaveJobRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Save a job for later.
    """
    supabase_url, headers, user_id = await get_supabase_client(authorization)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not supabase_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Check if already saved
    async with httpx.AsyncClient() as client:
        check_resp = await client.get(
            f"{supabase_url}/rest/v1/saved_jobs?user_id=eq.{user_id}&job_id=eq.{job.job_id}",
            headers=headers
        )
        if check_resp.status_code == 200 and check_resp.json():
            return {"message": "Job already saved", "saved": True}
    
    # Insert new saved job
    job_data = {
        "user_id": user_id,
        "job_id": job.job_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "apply_url": job.apply_url,
        "match_score": job.match_score,
        "matched_skills": job.matched_skills,
        "missing_skills": job.missing_skills
    }
    
    async with httpx.AsyncClient() as client:
        insert_resp = await client.post(
            f"{supabase_url}/rest/v1/saved_jobs",
            json=job_data,
            headers=headers
        )
        
        if insert_resp.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail="Failed to save job")
    
    return {"message": "Job saved successfully", "saved": True}


@router.get("/saved")
async def get_saved_jobs(
    page: int = Query(DEFAULT_PAGE, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    authorization: Optional[str] = Header(None)
):
    """
    Get all saved jobs for the user.
    """
    supabase_url, headers, user_id = await get_supabase_client(authorization)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not supabase_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Get saved jobs
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/saved_jobs?user_id=eq.{user_id}&order=saved_at.desc&limit={limit}&offset={(page-1)*limit}",
            headers=headers
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch saved jobs")
        
        saved_jobs = resp.json()
        
        # Get total count
        count_resp = await client.get(
            f"{supabase_url}/rest/v1/saved_jobs?user_id=eq.{user_id}&select=id",
            headers=headers
        )
        total = len(count_resp.json()) if count_resp.status_code == 200 else 0
    
    return {
        "jobs": saved_jobs,
        "count": len(saved_jobs),
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.delete("/saved/{job_id}")
async def unsave_job(
    job_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Remove a saved job.
    """
    supabase_url, headers, user_id = await get_supabase_client(authorization)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not supabase_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/saved_jobs?user_id=eq.{user_id}&job_id=eq.{job_id}",
            headers=headers
        )
        
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=500, detail="Failed to remove saved job")
    
    return {"message": "Job removed from saved", "removed": True}


# =============================================================================
# APPLICATION TRACKING ENDPOINTS
# =============================================================================

@router.post("/apply")
async def apply_to_job(
    job: ApplyJobRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Mark a job as applied. Also saves the job.
    """
    supabase_url, headers, user_id = await get_supabase_client(authorization)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not supabase_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Check if already applied
    async with httpx.AsyncClient() as client:
        check_resp = await client.get(
            f"{supabase_url}/rest/v1/job_applications?user_id=eq.{user_id}&job_id=eq.{job.job_id}",
            headers=headers
        )
        if check_resp.status_code == 200 and check_resp.json():
            return {"message": "Already applied to this job", "applied": True, "status": check_resp.json()[0]["status"]}
    
    # Create application record
    application_data = {
        "user_id": user_id,
        "job_id": job.job_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "apply_url": job.apply_url,
        "match_score": job.match_score,
        "matched_skills": job.matched_skills,
        "missing_skills": job.missing_skills,
        "status": "applied"
    }
    
    async with httpx.AsyncClient() as client:
        # Also save the job
        save_resp = await client.post(
            f"{supabase_url}/rest/v1/saved_jobs",
            json={
                "user_id": user_id,
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "apply_url": job.apply_url,
                "match_score": job.match_score,
                "matched_skills": job.matched_skills,
                "missing_skills": job.missing_skills
            },
            headers=headers
        )
        
        # Create application
        app_resp = await client.post(
            f"{supabase_url}/rest/v1/job_applications",
            json=application_data,
            headers=headers
        )
        
        if app_resp.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail="Failed to record application")
    
    return {"message": "Application recorded", "applied": True, "status": "applied"}


@router.get("/applications")
async def get_applications(
    page: int = Query(DEFAULT_PAGE, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    status: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """
    Get all job applications for the user.
    """
    supabase_url, headers, user_id = await get_supabase_client(authorization)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not supabase_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Build query
    query = f"user_id=eq.{user_id}&order=applied_at.desc&limit={limit}&offset={(page-1)*limit}"
    if status:
        query = f"user_id=eq.{user_id}&status=eq.{status}&order=applied_at.desc&limit={limit}&offset={(page-1)*limit}"
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/job_applications?{query}",
            headers=headers
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch applications")
        
        applications = resp.json()
        
        # Get total count
        count_query = f"user_id=eq.{user_id}"
        if status:
            count_query += f"&status=eq.{status}"
        count_resp = await client.get(
            f"{supabase_url}/rest/v1/job_applications?{count_query}&select=id",
            headers=headers
        )
        total = len(count_resp.json()) if count_resp.status_code == 200 else 0
    
    # Get status counts
    async with httpx.AsyncClient() as client:
        status_counts = {}
        for s in ['applied', 'interview', 'rejected', 'offer']:
            status_resp = await client.get(
                f"{supabase_url}/rest/v1/job_applications?user_id=eq.{user_id}&status=eq.{s}&select=id",
                headers=headers
            )
            status_counts[s] = len(status_resp.json()) if status_resp.status_code == 200 else 0
    
    return {
        "applications": applications,
        "count": len(applications),
        "total": total,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        },
        "status_counts": status_counts
    }


@router.put("/applications/{job_id}")
async def update_application(
    job_id: str,
    update: UpdateApplicationRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Update application status.
    """
    supabase_url, headers, user_id = await get_supabase_client(authorization)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not supabase_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Validate status
    valid_statuses = ['applied', 'interview', 'rejected', 'offer']
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    update_data = {
        "status": update.status,
        "updated_at": "now()"
    }
    
    if update.notes is not None:
        update_data["notes"] = update.notes
    
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{supabase_url}/rest/v1/job_applications?user_id=eq.{user_id}&job_id=eq.{job_id}",
            json=update_data,
            headers=headers
        )
        
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=500, detail="Failed to update application")
    
    return {"message": "Application updated", "status": update.status}


@router.delete("/applications/{job_id}")
async def withdraw_application(
    job_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Withdraw/delete an application.
    """
    supabase_url, headers, user_id = await get_supabase_client(authorization)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not supabase_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/job_applications?user_id=eq.{user_id}&job_id=eq.{job_id}",
            headers=headers
        )
        
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=500, detail="Failed to withdraw application")
    
    return {"message": "Application withdrawn", "withdrawn": True}
