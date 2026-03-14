"""
LeetCode API Service
Fetches user data from LeetCode using GraphQL API
"""
import httpx

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

async def get_user_stats(username: str) -> dict:
    """
    Fetch LeetCode user statistics.
    """
    query = """
    query getUserProfile($username: String!) {
        matchedUser(username: $username) {
            username
            submitStatsGlobal {
                submissionNumber
            }
            problemsSolvedBeStats {
                difficulty
                count
            }
        }
    }
    """
    
    variables = {"username": username}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        data = response.json()
        
        if "data" not in data or not data["data"].get("matchedUser"):
            return {"error": "User not found"}
        
        return data["data"]["matchedUser"]

async def get_contest_rating(username: str) -> dict:
    """
    Fetch user's contest rating.
    """
    query = """
    query userContestRankingInfo($username: String!) {
        userContestRanking(username: $username) {
            rating
            topPercentage
        }
    }
    """
    
    variables = {"username": username}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        data = response.json()
        
        return data.get("data", {}).get("userContestRanking", {})
