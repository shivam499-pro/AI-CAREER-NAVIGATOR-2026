"""
GitHub API Service
Fetches real user data from GitHub REST API
"""
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_API_URL = "https://api.github.com"

async def get_user_profile(username: str) -> dict:
    """
    Fetch GitHub user profile.
    Returns: name, bio, followers, following, public_repos, location, company, blog
    """
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GITHUB_API_URL}/users/{username}",
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            user_data = response.json()
            
            return {
                "username": user_data.get("login"),
                "name": user_data.get("name"),
                "bio": user_data.get("bio"),
                "followers": user_data.get("followers"),
                "following": user_data.get("following"),
                "public_repos": user_data.get("public_repos"),
                "location": user_data.get("location"),
                "company": user_data.get("company"),
                "blog": user_data.get("blog"),
                "avatar_url": user_data.get("avatar_url"),
                "html_url": user_data.get("html_url"),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub user not found: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

async def get_user_repos(username: str, limit: int = 30) -> list:
    """
    Fetch user's repositories.
    Returns: name, language, stars, forks, description, html_url, updated_at
    """
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GITHUB_API_URL}/users/{username}/repos",
                params={
                    "sort": "updated",
                    "per_page": limit,
                    "direction": "desc"
                },
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            repos_data = response.json()
            
            repos = []
            for repo in repos_data:
                repos.append({
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "language": repo.get("language"),
                    "stars": repo.get("stargazers_count"),
                    "forks": repo.get("forks_count"),
                    "description": repo.get("description"),
                    "html_url": repo.get("html_url"),
                    "updated_at": repo.get("updated_at"),
                    "topics": repo.get("topics", [])[:5],  # Top 5 topics
                })
            
            return repos
        except Exception as e:
            return [{"error": str(e)}]

async def get_top_repos(username: str, limit: int = 5) -> list:
    """
    Get user's top repositories by stars.
    """
    repos = await get_user_repos(username, limit=100)
    
    if isinstance(repos, dict) and "error" in repos:
        return repos
    
    # Sort by stars and return top N
    sorted_repos = sorted(
        [r for r in repos if r.get("stars", 0) > 0],
        key=lambda x: x.get("stars", 0),
        reverse=True
    )
    
    return sorted_repos[:limit]

async def get_language_stats(username: str) -> dict:
    """
    Get language statistics across all repositories.
    Returns count of repos per language.
    """
    repos = await get_user_repos(username, limit=100)
    
    if isinstance(repos, dict) and "error" in repos:
        return repos
    
    language_stats = {}
    for repo in repos:
        if repo.get("language"):
            lang = repo["language"]
            language_stats[lang] = language_stats.get(lang, 0) + 1
    
    # Sort by count and return
    sorted_stats = dict(
        sorted(language_stats.items(), key=lambda x: x[1], reverse=True)
    )
    
    return sorted_stats

async def get_contribution_stats(username: str) -> dict:
    """
    Get contribution statistics from GitHub.
    Note: This requires authenticated access for accurate data.
    """
    user_profile = await get_user_profile(username)
    
    if isinstance(user_profile, dict) and "error" in user_profile:
        return user_profile
    
    return {
        "public_repos": user_profile.get("public_repos", 0),
        "followers": user_profile.get("followers", 0),
        "following": user_profile.get("following", 0),
    }

async def get_full_github_data(username: str) -> dict:
    """
    Get complete GitHub data for a user.
    Combines profile, top repos, and language stats.
    """
    profile = await get_user_profile(username)
    
    if isinstance(profile, dict) and "error" in profile:
        return profile
    
    top_repos = await get_top_repos(username)
    language_stats = await get_language_stats(username)
    contribution_stats = await get_contribution_stats(username)
    
    return {
        "profile": profile,
        "top_repos": top_repos,
        "language_stats": language_stats,
        "contribution_stats": contribution_stats,
    }
