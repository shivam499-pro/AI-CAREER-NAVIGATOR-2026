import httpx
import pytest

from services.github_service import (
    get_user_profile,
    get_user_repos,
    get_top_repos,
    get_language_stats,
    get_contribution_stats,
    get_full_github_data,
)


# ============================================================================
# MOCK HELPERS
# ============================================================================

class MockResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.github.com/test")
            response = httpx.Response(
                status_code=self.status_code,
                request=request,
            )
            raise httpx.HTTPStatusError(
                "HTTP Error",
                request=request,
                response=response,
            )


class MockAsyncClient:
    def __init__(self, response=None, exception=None):
        self.response = response
        self.exception = exception

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        if self.exception:
            raise self.exception
        return self.response


# ============================================================================
# PROFILE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_profile_success(mocker, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    payload = {
        "login": "jaisuu",
        "name": "Jaisuu",
        "bio": "Developer",
        "followers": 100,
        "following": 20,
        "public_repos": 50,
        "location": "India",
        "company": "OpenAI",
        "blog": "https://blog.com",
        "avatar_url": "avatar",
        "html_url": "profile",
    }

    mock_client = MockAsyncClient(
        response=MockResponse(payload)
    )

    mocker.patch(
        "services.github_service.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = await get_user_profile("jaisuu")

    assert result["username"] == "jaisuu"
    assert result["followers"] == 100
    assert result["public_repos"] == 50


@pytest.mark.asyncio
async def test_get_user_profile_without_token(mocker, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    payload = {
        "login": "testuser"
    }

    mock_client = MockAsyncClient(
        response=MockResponse(payload)
    )

    mocker.patch(
        "services.github_service.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = await get_user_profile("testuser")

    assert result["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_user_profile_404(mocker):
    mock_client = MockAsyncClient(
        response=MockResponse({}, status_code=404)
    )

    mocker.patch(
        "services.github_service.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = await get_user_profile("unknown")

    assert "error" in result
    assert "GitHub user not found" in result["error"]


@pytest.mark.asyncio
async def test_get_user_profile_rate_limit(mocker):
    mock_client = MockAsyncClient(
        response=MockResponse({}, status_code=403)
    )

    mocker.patch(
        "services.github_service.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = await get_user_profile("limited")

    assert "error" in result


@pytest.mark.asyncio
async def test_get_user_profile_timeout(mocker):
    mock_client = MockAsyncClient(
        exception=httpx.TimeoutException("timeout")
    )

    mocker.patch(
        "services.github_service.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = await get_user_profile("timeout-user")

    assert "error" in result


# ============================================================================
# REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_repos_success(mocker):
    repos_payload = [
        {
            "name": "repo1",
            "full_name": "user/repo1",
            "language": "Python",
            "stargazers_count": 20,
            "forks_count": 5,
            "description": "repo",
            "html_url": "url",
            "updated_at": "today",
            "topics": ["ai", "ml", "python", "fastapi", "backend", "extra"],
        }
    ]

    mock_client = MockAsyncClient(
        response=MockResponse(repos_payload)
    )

    mocker.patch(
        "services.github_service.httpx.AsyncClient",
        return_value=mock_client,
    )

    repos = await get_user_repos("user")

    assert len(repos) == 1
    assert repos[0]["name"] == "repo1"
    assert len(repos[0]["topics"]) == 5


@pytest.mark.asyncio
async def test_get_user_repos_exception(mocker):
    mock_client = MockAsyncClient(
        exception=httpx.TimeoutException("timeout")
    )

    mocker.patch(
        "services.github_service.httpx.AsyncClient",
        return_value=mock_client,
    )

    repos = await get_user_repos("user")

    assert isinstance(repos, list)
    assert "error" in repos[0]


# ============================================================================
# TOP REPOS
# ============================================================================

@pytest.mark.asyncio
async def test_get_top_repos_sorted_by_stars(mocker):
    repos = [
        {"name": "repo1", "stars": 5},
        {"name": "repo2", "stars": 50},
        {"name": "repo3", "stars": 25},
        {"name": "repo4", "stars": 0},
    ]

    mocker.patch(
        "services.github_service.get_user_repos",
        return_value=repos,
    )

    result = await get_top_repos("user", limit=2)

    assert len(result) == 2
    assert result[0]["stars"] == 50
    assert result[1]["stars"] == 25


@pytest.mark.asyncio
async def test_get_top_repos_error_passthrough(mocker):
    error = {"error": "failure"}

    mocker.patch(
        "services.github_service.get_user_repos",
        return_value=error,
    )

    result = await get_top_repos("user")

    assert result == error


# ============================================================================
# LANGUAGE STATS
# ============================================================================

@pytest.mark.asyncio
async def test_get_language_stats_aggregation(mocker):
    repos = [
        {"language": "Python"},
        {"language": "Python"},
        {"language": "TypeScript"},
        {"language": "Java"},
        {"language": None},
    ]

    mocker.patch(
        "services.github_service.get_user_repos",
        return_value=repos,
    )

    stats = await get_language_stats("user")

    assert stats["Python"] == 2
    assert stats["TypeScript"] == 1
    assert stats["Java"] == 1

@pytest.mark.asyncio
async def test_get_language_stats_error_passthrough(mocker):
    error = {"error": "repo failure"}

    mocker.patch(
        "services.github_service.get_user_repos",
        return_value=error,
    )

    result = await get_language_stats("user")

    assert result == error
# ============================================================================
# CONTRIBUTION STATS
# ============================================================================

@pytest.mark.asyncio
async def test_get_contribution_stats(mocker):
    profile = {
        "public_repos": 30,
        "followers": 100,
        "following": 15,
    }

    mocker.patch(
        "services.github_service.get_user_profile",
        return_value=profile,
    )

    result = await get_contribution_stats("user")

    assert result["public_repos"] == 30
    assert result["followers"] == 100
    assert result["following"] == 15

@pytest.mark.asyncio
async def test_get_contribution_stats_error_passthrough(mocker):
    error = {"error": "profile failure"}

    mocker.patch(
        "services.github_service.get_user_profile",
        return_value=error,
    )

    result = await get_contribution_stats("user")

    assert result == error
# ============================================================================
# FULL DATA AGGREGATION
# ============================================================================

@pytest.mark.asyncio
async def test_get_full_github_data(mocker):
    mocker.patch(
        "services.github_service.get_user_profile",
        return_value={"username": "user"},
    )

    mocker.patch(
        "services.github_service.get_top_repos",
        return_value=[{"name": "repo"}],
    )

    mocker.patch(
        "services.github_service.get_language_stats",
        return_value={"Python": 2},
    )

    mocker.patch(
        "services.github_service.get_contribution_stats",
        return_value={"followers": 10},
    )

    result = await get_full_github_data("user")

    assert result["profile"]["username"] == "user"
    assert result["top_repos"][0]["name"] == "repo"
    assert result["language_stats"]["Python"] == 2


@pytest.mark.asyncio
async def test_get_full_github_data_profile_error(mocker):
    error = {"error": "profile failed"}

    mocker.patch(
        "services.github_service.get_user_profile",
        return_value=error,
    )

    result = await get_full_github_data("user")

    assert result == error