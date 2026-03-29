from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services import jobs_service

router = APIRouter()

@router.get("/")
async def get_jobs(
    query: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    keywords: Optional[str] = Query(None)
):
    """
    Get job suggestions based on user profile and filters.
    """
    try:
        # Use the query provided or fallback to keywords/mock
        search_query = query or keywords
        
        if search_query:
            results = await jobs_service.search_jobs(search_query, location)
            return {
                "jobs": results,
                "count": len(results)
            }
        
        # Fallback to mock job data if no search query
        mock_jobs = [
            {
                "id": "1",
                "title": "Frontend Developer",
                "company": "Tech Corp",
                "location": "Remote",
                "type": "Full-time",
                "url": "https://linkedin.com/jobs/view/123",
                "match_score": 92
            },
            {
                "id": "2",
                "title": "Full Stack Developer",
                "company": "StartupXYZ",
                "location": "San Francisco, CA",
                "type": "Full-time",
                "url": "https://linkedin.com/jobs/view/456",
                "match_score": 88
            },
            {
                "id": "3",
                "title": "Junior Software Engineer",
                "company": "BigTech Inc",
                "location": "New York, NY",
                "type": "Internship",
                "url": "https://internshala.com/job/view/789",
                "match_score": 85
            }
        ]
        
        # Apply filters to mock data
        if location:
            mock_jobs = [j for j in mock_jobs if location.lower() in j["location"].lower()]
        if job_type:
            mock_jobs = [j for j in mock_jobs if job_type.lower() in j["type"].lower()]
            
        return {
            "jobs": mock_jobs,
            "count": len(mock_jobs)
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
