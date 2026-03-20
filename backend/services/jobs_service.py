"""
Jobs Service
Aggregates job listings from various sources
"""
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def search_jobs(query: str, location: str = None) -> list:
    """
    Search for jobs using SerpAPI (Google Jobs).
    """
    api_key = os.getenv("SERPAPI_KEY")
    
    if not api_key:
        return get_mock_jobs(query, location)
    
    params = {
        "q": f"{query} jobs",
        "api_key": api_key,
        "engine": "google_jobs"
    }
    
    if location:
        params["location"] = location
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://serpapi.com/search",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for job in data.get("jobs_results", [])[:10]:
            jobs.append({
                "id": job.get("job_id", ""),
                "title": job.get("title", ""),
                "company": job.get("company_name", ""),
                "location": job.get("location", ""),
                "type": job.get("job_type", ""),
                "url": job.get("url", ""),
                "match_score": 80  # Placeholder
            })
        
        return jobs

def get_mock_jobs(query: str, location: str = None) -> list:
    """
    Return mock job data for development.
    """
    return [
        {
            "id": "1",
            "title": "Frontend Developer",
            "company": "Tech Corp",
            "location": location or "Remote",
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

def get_linkedin_jobs_url(keywords: str, location: str = None) -> str:
    """
    Generate LinkedIn job search URL.
    """
    base_url = "https://www.linkedin.com/jobs/search/"
    params = f"?keywords={keywords.replace(' ', '%20')}"
    
    if location:
        params += f"&location={location.replace(' ', '%20')}"
    
    return base_url + params

def get_internship_url(keywords: str) -> str:
    """
    Generate Internshala job search URL.
    """
    return f"https://www.internshala.com/jobs/search/{keywords.replace(' ', '-')}"
