import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx

import services.leetcode_service as leetcode_service


# ---------------------------
# Helpers
# ---------------------------

def mock_response(json_data=None, status_code=200, raise_http=False):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data or {}

    if raise_http:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error",
            request=MagicMock(),
            response=MagicMock(status_code=status_code),
        )
    else:
        mock_resp.raise_for_status.return_value = None

    return mock_resp


def mock_client(mock_resp):
    client = MagicMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False

    client.post = AsyncMock(return_value=mock_resp)
    return client


# ---------------------------
# get_user_profile
# ---------------------------
@pytest.mark.asyncio
async def test_get_user_profile_exception_branch(mocker):
    from services import leetcode_service

    async def raise_error(*args, **kwargs):
        raise Exception("network failure")

    mock_client = mocker.patch("httpx.AsyncClient")
    mock_client.return_value.__aenter__.return_value.post.side_effect = raise_error

    result = await leetcode_service.get_user_profile("john")

    assert "error" in result

@pytest.mark.asyncio
async def test_get_user_profile_missing_data(mocker):
    from services import leetcode_service

    payload = {"data": {}}

    mock_resp = mock_response(json_data=payload)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_user_profile("john")

    assert result["error"] == "User not found"

@pytest.mark.asyncio
async def test_get_user_profile_success(mocker):
    data = {
        "data": {
            "matchedUser": {
                "username": "john",
                "profile": {
                    "realName": "John Doe",
                    "userAvatar": "avatar.png",
                    "aboutMe": "coder",
                    "school": "ABC",
                    "company": "XYZ",
                    "location": "India",
                    "skillTags": ["python", "js"]
                }
            }
        }
    }

    mock_resp = mock_response(json_data=data)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_user_profile("john")

    assert result["username"] == "john"
    assert result["real_name"] == "John Doe"
    assert "skill_tags" in result

@pytest.mark.asyncio
async def test_get_problems_solved_success(mocker):
    data = {
        "data": {
            "matchedUser": {
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "All", "count": 500},
                        {"difficulty": "Easy", "count": 200},
                        {"difficulty": "Medium", "count": 250},
                        {"difficulty": "Hard", "count": 50},
                    ]
                }
            }
        }
    }

    mock_resp = mock_response(json_data=data)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_problems_solved("testuser")

    assert result == {
        "total": 500,
        "easy": 200,
        "medium": 250,
        "hard": 50,
    }
@pytest.mark.asyncio
async def test_get_contest_rating_empty_data(mocker):
    from services import leetcode_service

    payload = {}

    mock_resp = mock_response(json_data=payload)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_contest_rating("john")

    assert result["rating"] == 0
    assert result["top_percentage"] == 100

@pytest.mark.asyncio
async def test_get_problems_solved_fallback(mocker):
    data = {
        "data": {
            "matchedUser": {
                "submitStats": {
                    "acSubmissionNum": None
                }
            }
        }
    }

    mock_resp = mock_response(json_data=data)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_problems_solved("testuser")

    assert result["total"] == 200
@pytest.mark.asyncio
async def test_recent_submissions_none_branch(mocker):
    from services import leetcode_service

    payload = {
        "data": {
            "recentSubmissionList": None
        }
    }

    mock_resp = mock_response(json_data=payload)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_recent_submissions("john")

    assert result == []

@pytest.mark.asyncio
async def test_full_leetcode_data_integration(mocker):
    from services import leetcode_service

    mocker.patch(
        "services.leetcode_service.get_user_profile",
        return_value={"username": "john"},
    )

    mocker.patch(
        "services.leetcode_service.get_problems_solved",
        return_value={"total": 10},
    )

    mocker.patch(
        "services.leetcode_service.get_contest_rating",
        return_value={"rating": 1500},
    )

    mocker.patch(
        "services.leetcode_service.get_recent_submissions",
        return_value=[{"title": "Two Sum"}],
    )

    result = await leetcode_service.get_full_leetcode_data("john")

    assert result["profile"]["username"] == "john"
    assert result["problems_solved"]["total"] == 10

@pytest.mark.asyncio
async def test_get_full_leetcode_data_success(mocker):
    mocker.patch("services.leetcode_service.get_user_profile", return_value={"username": "user"})
    mocker.patch("services.leetcode_service.get_problems_solved", return_value={"total": 100})
    mocker.patch("services.leetcode_service.get_contest_rating", return_value={"rating": 1500})
    mocker.patch("services.leetcode_service.get_recent_submissions", return_value=[{"title": "Two Sum"}])

    result = await leetcode_service.get_full_leetcode_data("user")

    assert result["profile"]["username"] == "user"
    assert result["problems_solved"]["total"] == 100
    assert result["contest_rating"]["rating"] == 1500
    assert len(result["recent_submissions"]) == 1

@pytest.mark.asyncio
async def test_get_user_profile_http_failure(mocker):
    import httpx
    from services import leetcode_service

    mock_resp = mock_response(status_code=500, raise_http=True)
    mocker.patch(
        "httpx.AsyncClient",
        return_value=mock_client(mock_resp)
    )

    result = await leetcode_service.get_user_profile("john")

    assert "error" in result

@pytest.mark.asyncio
async def test_get_problems_user_not_found_branch(mocker):
    from services import leetcode_service

    payload = {"data": {"matchedUser": None}}

    mock_resp = mock_response(json_data=payload)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_problems_solved("ghost")

    assert result["error"] == "User not found"

@pytest.mark.asyncio
async def test_get_problems_fallback_total_calculation(mocker):
    from services import leetcode_service

    payload = {
        "data": {
            "matchedUser": {
                "submitStats": {
                    "acSubmissionNum": [
                        {"difficulty": "Easy", "count": 10},
                        {"difficulty": "Medium", "count": 20},
                        {"difficulty": "Hard", "count": 30},
                    ]
                }
            }
        }
    }

    mock_resp = mock_response(json_data=payload)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_problems_solved("john")

    assert result["total"] == 60

@pytest.mark.asyncio
async def test_get_recent_submissions_empty(mocker):
    from services import leetcode_service

    payload = {"data": {"recentSubmissionList": []}}

    mock_resp = mock_response(json_data=payload)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_recent_submissions("john")

    assert result == []


@pytest.mark.asyncio
async def test_get_problems_malformed_stats(mocker):
    from services import leetcode_service

    payload = {
        "data": {
            "matchedUser": {
                "submitStats": {
                    "acSubmissionNum": None
                }
            }
        }
    }

    mock_resp = mock_response(json_data=payload)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_problems_solved("john")

    assert result["total"] == 200

@pytest.mark.asyncio
async def test_get_problems_solved_skips_non_dict_entries(mocker):
    """A malformed non-dict entry mixed into acSubmissionNum is skipped,
    not allowed to crash the whole aggregation."""
    payload = {
        "data": {
            "matchedUser": {
                "submitStats": {
                    "acSubmissionNum": [
                        "not-a-dict",
                        {"difficulty": "Easy", "count": 10},
                    ]
                }
            }
        }
    }

    mock_resp = mock_response(json_data=payload)
    mocker.patch("httpx.AsyncClient", return_value=mock_client(mock_resp))

    result = await leetcode_service.get_problems_solved("john")

    assert result["easy"] == 10
    assert result["total"] == 10


@pytest.mark.asyncio
async def test_get_problems_solved_exception_branch(mocker):
    async def raise_error(*args, **kwargs):
        raise Exception("network failure")

    mock_client_patch = mocker.patch("httpx.AsyncClient")
    mock_client_patch.return_value.__aenter__.return_value.post.side_effect = raise_error

    result = await leetcode_service.get_problems_solved("john")

    assert result == {"error": "LeetCode service unavailable"}


@pytest.mark.asyncio
async def test_get_contest_rating_exception_branch(mocker):
    async def raise_error(*args, **kwargs):
        raise Exception("network failure")

    mock_client_patch = mocker.patch("httpx.AsyncClient")
    mock_client_patch.return_value.__aenter__.return_value.post.side_effect = raise_error

    result = await leetcode_service.get_contest_rating("john")

    assert result == {
        "rating": 0,
        "top_percentage": 100,
        "contests_attended": 0,
        "history": [],
    }


@pytest.mark.asyncio
async def test_get_recent_submissions_exception_branch(mocker):
    async def raise_error(*args, **kwargs):
        raise Exception("network failure")

    mock_client_patch = mocker.patch("httpx.AsyncClient")
    mock_client_patch.return_value.__aenter__.return_value.post.side_effect = raise_error

    result = await leetcode_service.get_recent_submissions("john")

    assert result == []