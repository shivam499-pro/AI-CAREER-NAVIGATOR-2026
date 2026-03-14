"""
GitHub API Service
Fetches user data from GitHub using the REST API
"""
import httpx
import os

GITHUB_API_URL = "https://api.github.com"

async def get_user_profile(username: str) -> dict:
    """
    Fetch GitHub user profile.
    """
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/users/{username}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

async def get_user_repos(username: str) -> list:
    """
    Fetch user's repositories.
    """
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/users/{username}/repos",
            params={"sort": "updated", "per_page": 100},
            headers=headers
        )
        response.raise_for_status()
        return response.json()

async def get_user_languages(username: str) -> dict:
    """
    Get language statistics across all repositories.
    """
    repos = await get_user_repos(username)
    
    language_stats = {}
    for repo in repos:
        if repo.get("language"):
            lang = repo["language"]
            language_stats[lang] = language_stats.get(lang, 0) + 1
    
    return language_stats

async def get_contribution_stats(username: str) -> dict:
    """
    Get user contribution statistics.
    """
    # This requires GraphQL API - simplified for now
    user = await get_user_profile(username)
    
    return {
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
    }
