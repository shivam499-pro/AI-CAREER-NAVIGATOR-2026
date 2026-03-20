"""
LeetCode API Service
Fetches real user data from LeetCode GraphQL API
"""
import httpx

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

async def get_user_profile(username: str) -> dict:
    """
    Fetch LeetCode user profile.
    """
    query = """
    query getUserProfile($username: String!) {
        matchedUser(username: $username) {
            username
            profile {
                realName
                userAvatar
                aboutMe
                school
                company
                location
                skillTags
            }
            submitStatsGlobal {
                totalSubmissionNum {
                    count
                }
            }
        }
    }
    """
    
    variables = {"username": username}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "data" not in data or not data["data"].get("matchedUser"):
                return {"error": "User not found"}
            
            user = data["data"]["matchedUser"]
            profile = user.get("profile", {})
            
            return {
                "username": user.get("username"),
                "real_name": profile.get("realName"),
                "avatar": profile.get("userAvatar"),
                "about_me": profile.get("aboutMe"),
                "school": profile.get("school"),
                "company": profile.get("company"),
                "location": profile.get("location"),
                "skill_tags": profile.get("skillTags", []),
                "total_submissions": user.get("submitStatsGlobal", {}).get("totalSubmissionNum", {}).get("count", 0),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"LeetCode user not found: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

async def get_problems_solved(username: str) -> dict:
    """
    Fetch user's problems solved statistics.
    Returns: total, easy, medium, hard breakdown
    """
    query = """
    query getProblemsSolved($username: String!) {
        matchedUser(username: $username) {
            problemsSolvedBeStats {
                difficulty
                count
                submissions
            }
        }
    }
    """
    
    variables = {"username": username}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "data" not in data or not data["data"].get("matchedUser"):
                return {"error": "User not found"}
            
            stats = data["data"]["matchedUser"].get("problemsSolvedBeStats", [])
            
            result = {
                "total": 0,
                "easy": 0,
                "medium": 0,
                "hard": 0,
            }
            
            for stat in stats:
                difficulty = stat.get("difficulty", "").lower()
                count = stat.get("count", 0)
                result["total"] += count
                if difficulty == "easy":
                    result["easy"] = count
                elif difficulty == "medium":
                    result["medium"] = count
                elif difficulty == "hard":
                    result["hard"] = count
            
            return result
        except Exception as e:
            return {"error": str(e)}

async def get_contest_rating(username: str) -> dict:
    """
    Fetch user's contest rating and ranking.
    """
    query = """
    query userContestRankingInfo($username: String!) {
        userContestRanking(username: $username) {
            rating
            topPercentage
            attendedContestsCount
        }
        userContestRankingHistory(username: $username) {
            contest {
                title
            }
            rating
            ranking
            totalParticipants
        }
    }
    """
    
    variables = {"username": username}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "data" not in data:
                return {"error": "No contest data"}
            
            contest_data = data["data"]
            ranking = contest_data.get("userContestRanking", {})
            
            return {
                "rating": ranking.get("rating", 0),
                "top_percentage": ranking.get("topPercentage", 100),
                "contests_attended": ranking.get("attendedContestsCount", 0),
                "history": contest_data.get("userContestRankingHistory", [])[:5],
            }
        except Exception as e:
            return {"error": str(e)}

async def get_recent_submissions(username: str, limit: int = 10) -> list:
    """
    Fetch recent submissions.
    """
    query = """
    query getRecentSubmissions($username: String!, $limit: Int!) {
        recentSubmissionList(username: $username, limit: $limit) {
            id
            title
            titleSlug
            status
            lang
            timestamp
        }
    }
    """
    
    variables = {"username": username, "limit": limit}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "data" not in data:
                return []
            
            submissions = data["data"].get("recentSubmissionList", [])
            
            return [
                {
                    "title": sub.get("title"),
                    "slug": sub.get("titleSlug"),
                    "status": sub.get("status"),
                    "language": sub.get("lang"),
                    "timestamp": sub.get("timestamp"),
                }
                for sub in submissions
            ]
        except Exception as e:
            return []

async def get_full_leetcode_data(username: str) -> dict:
    """
    Get complete LeetCode data for a user.
    """
    profile = await get_user_profile(username)
    
    if isinstance(profile, dict) and "error" in profile:
        return profile
    
    problems_solved = await get_problems_solved(username)
    contest_rating = await get_contest_rating(username)
    recent_subs = await get_recent_submissions(username)
    
    return {
        "profile": profile,
        "problems_solved": problems_solved,
        "contest_rating": contest_rating,
        "recent_submissions": recent_subs,
    }
