import httpx

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"


# =========================================================
# USER PROFILE
# =========================================================
async def get_user_profile(username: str) -> dict:
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
        }
    }
    """

    variables = {"username": username}

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30.0,
            )
            res.raise_for_status()
            data = res.json()

            if not data.get("data", {}).get("matchedUser"):
                return {"error": "User not found"}

            user = data["data"]["matchedUser"]
            profile = user.get("profile") or {}

            return {
                "username": user.get("username"),
                "real_name": profile.get("realName"),
                "avatar": profile.get("userAvatar"),
                "about_me": profile.get("aboutMe"),
                "school": profile.get("school"),
                "company": profile.get("company"),
                "location": profile.get("location"),
                "skill_tags": profile.get("skillTags", []),
            }

        except httpx.HTTPStatusError:
            return {"error": "LeetCode user not found"}
        except Exception:
            return {"error": "LeetCode service unavailable"}


# =========================================================
# PROBLEMS SOLVED
# =========================================================
async def get_problems_solved(username: str) -> dict:
    query = """
    query getUserSolvedStats($username: String!) {
        matchedUser(username: $username) {
            submitStats {
                acSubmissionNum {
                    difficulty
                    count
                }
            }
        }
    }
    """

    variables = {"username": username}

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30.0,
            )
            res.raise_for_status()
            data = res.json()

            if not data.get("data", {}).get("matchedUser"):
                return {"error": "User not found"}

            stats = (
                data["data"]["matchedUser"]
                .get("submitStats", {})
                .get("acSubmissionNum")
            )

            if not isinstance(stats, list):
                return {"total": 200, "easy": 0, "medium": 0, "hard": 0}

            result = {"total": 0, "easy": 0, "medium": 0, "hard": 0}

            for s in stats:
                if not isinstance(s, dict):
                    continue

                diff = (s.get("difficulty") or "").lower()
                count = s.get("count", 0)

                if diff == "all":
                    result["total"] = count
                elif diff == "easy":
                    result["easy"] = count
                elif diff == "medium":
                    result["medium"] = count
                elif diff == "hard":
                    result["hard"] = count

            if result["total"] == 0:
                result["total"] = result["easy"] + result["medium"] + result["hard"]

            return result

    except Exception:
        return {"error": "LeetCode service unavailable"}


# =========================================================
# CONTEST RATING
# =========================================================
async def get_contest_rating(username: str) -> dict:
    query = """
    query userContestRankingInfo($username: String!) {
        userContestRanking(username: $username) {
            rating
            topPercentage
            attendedContestsCount
        }
        userContestRankingHistory(username: $username) {
            contest { title }
            rating
            ranking
            totalParticipants
        }
    }
    """

    variables = {"username": username}

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30.0,
            )
            res.raise_for_status()
            data = res.json()

            ranking = data.get("data", {}).get("userContestRanking") or {}

            return {
                "rating": ranking.get("rating", 0),
                "top_percentage": ranking.get("topPercentage", 100),
                "contests_attended": ranking.get("attendedContestsCount", 0),
                "history": (data.get("data", {}).get("userContestRankingHistory") or [])[:5],
            }

    except Exception:
        return {
            "rating": 0,
            "top_percentage": 100,
            "contests_attended": 0,
            "history": [],
        }


# =========================================================
# RECENT SUBMISSIONS
# =========================================================
async def get_recent_submissions(username: str, limit: int = 10) -> list:
    query = """
    query getRecentSubmissions($username: String!, $limit: Int!) {
        recentSubmissionList(username: $username, limit: $limit) {
            title
            titleSlug
            status
            lang
            timestamp
        }
    }
    """

    variables = {"username": username, "limit": limit}

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30.0,
            )
            res.raise_for_status()
            data = res.json()

            subs = data.get("data", {}).get("recentSubmissionList") or []

            return [
                {
                    "title": s.get("title"),
                    "slug": s.get("titleSlug"),
                    "status": s.get("status"),
                    "language": s.get("lang"),
                    "timestamp": s.get("timestamp"),
                }
                for s in subs
                if isinstance(s, dict)
            ]

    except Exception:
        return []


# =========================================================
# FULL AGGREGATION
# =========================================================
async def get_full_leetcode_data(username: str) -> dict:
    return {
        "profile": await get_user_profile(username),
        "problems_solved": await get_problems_solved(username),
        "contest_rating": await get_contest_rating(username),
        "recent_submissions": await get_recent_submissions(username),
    }