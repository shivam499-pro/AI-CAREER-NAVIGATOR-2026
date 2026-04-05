from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services import jobs_service

router = APIRouter()

# Default pagination settings
DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 50


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


@router.get("/")
async def get_jobs(
    query: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    keywords: Optional[str] = Query(None),
    page: int = Query(DEFAULT_PAGE, ge=1, description="Page number"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Items per page")
):
    """
    Get job suggestions based on user profile and filters.
    Supports pagination with page and limit query parameters.
    """
    try:
        # Use the query provided or fallback to keywords/mock
        search_query = query or keywords
        
        if search_query:
            results = await jobs_service.search_jobs(search_query, location)
            paginated = paginate_response(results, page, limit)
            return {
                "jobs": paginated["data"],
                "count": len(paginated["data"]),
                "pagination": paginated["pagination"]
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
        
        # Paginate results
        paginated = paginate_response(mock_jobs, page, limit)
        
        return {
            "jobs": paginated["data"],
            "count": len(paginated["data"]),
            "pagination": paginated["pagination"]
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
