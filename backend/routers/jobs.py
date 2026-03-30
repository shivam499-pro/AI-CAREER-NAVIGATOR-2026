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
                "title": f"Junior {search_query or 'Software Engineer'}",
                "company": "Tech Solutions India",
                "location": "Remote, India",
                "type": "Full-time",
                "url": "#",
                "match_score": 92
            },
            {
                "id": "2",
                "title": f"{search_query or 'Full Stack Developer'}",
                "company": "Global Dev Center",
                "location": "Bangalore / Remote",
                "type": "Full-time",
                "url": "#",
                "match_score": 88
            },
            {
                "id": "3",
                "title": f"Intern - {search_query or 'Systems Engineer'}",
                "company": "Innovate Labs",
                "location": "Chennai, India",
                "type": "Internship",
                "url": "#",
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
