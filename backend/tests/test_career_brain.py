"""
Tests for routers/career_brain.py

Coverage targets (24 missing lines → 100%):
- Missing Authorization header → 401
- Header not starting with 'Bearer ' → 401
- SUPABASE_URL / SUPABASE_SERVICE_KEY not set → 500
- Supabase auth call returns non-200 → 401
- Supabase auth call returns 200 but no 'id' field → 401
- career_brain_service raises exception → 500
- Full happy path → 200
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.career_brain import router

# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(router, prefix="/brain")
client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared mock response helpers
# ---------------------------------------------------------------------------

VALID_USER_RESPONSE = {"id": "user-xyz-999", "email": "dev@example.com"}
CAREER_BRAIN_RESULT = {
    "job_readiness_score": 78,
    "skill_analysis": {"strong": ["Python"], "weak": ["System Design"]},
    "recommendations": ["Study distributed systems"],
}


def _mock_httpx_success(user_data: dict = None):
    """Build an httpx mock that returns 200 with user_data."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = user_data or VALID_USER_RESPONSE
    return mock_resp


def _mock_httpx_failure(status_code: int = 401):
    """Build an httpx mock that returns a non-200 status."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"error": "Unauthorized"}
    return mock_resp


# ===========================================================================
# Authorization header validation
# ===========================================================================


class TestAuthorizationHeader:
    def test_missing_authorization_header_returns_401(self):
        """No Authorization header at all → 401."""
        resp = client.get("/brain/career-brain")
        assert resp.status_code == 401
        assert "Authentication required" in resp.json()["detail"]

    def test_authorization_without_bearer_prefix_returns_401(self):
        """Header present but doesn't start with 'Bearer ' → 401."""
        resp = client.get(
            "/brain/career-brain",
            headers={"Authorization": "Token abc123"},
        )
        assert resp.status_code == 401
        assert "Authentication required" in resp.json()["detail"]

    def test_empty_authorization_header_returns_401(self):
        """Empty string Authorization → 401."""
        resp = client.get(
            "/brain/career-brain",
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401

    def test_bearer_lowercase_returns_401(self):
        """'bearer ' (lowercase) is not accepted — must be exact 'Bearer '."""
        resp = client.get(
            "/brain/career-brain",
            headers={"Authorization": "bearer token123"},
        )
        assert resp.status_code == 401


# ===========================================================================
# Supabase environment configuration
# ===========================================================================


class TestSupabaseConfiguration:
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_supabase_url_returns_500(self):
        """SUPABASE_URL not set → 500 database not configured."""
        resp = client.get(
            "/brain/career-brain",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert resp.status_code == 500
        assert "Database not configured" in resp.json()["detail"]

    @patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co"}, clear=True)
    def test_missing_supabase_key_returns_500(self):
        """SUPABASE_URL set but both key env vars missing → 500."""
        resp = client.get(
            "/brain/career-brain",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert resp.status_code == 500
        assert "Database not configured" in resp.json()["detail"]


# ===========================================================================
# Supabase token validation
# ===========================================================================


class TestTokenValidation:
    @patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-key-xyz",
        },
    )
    @patch("routers.career_brain.httpx.AsyncClient")
    def test_invalid_token_returns_401(self, mock_async_client):
        """Supabase /auth/v1/user returns non-200 → 401 Invalid token."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=_mock_httpx_failure(401))
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get(
            "/brain/career-brain",
            headers={"Authorization": "Bearer expired-token"},
        )

        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["detail"]

    @patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-key-xyz",
        },
    )
    @patch("routers.career_brain.httpx.AsyncClient")
    def test_missing_user_id_in_response_returns_401(self, mock_async_client):
        """Supabase returns 200 but no 'id' field → 401 User not found."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            return_value=_mock_httpx_success({"email": "user@example.com"})  # no 'id'
        )
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get(
            "/brain/career-brain",
            headers={"Authorization": "Bearer some-token"},
        )

        assert resp.status_code == 401
        assert "User not found" in resp.json()["detail"]

    @patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-key-xyz",
        },
    )
    @patch("routers.career_brain.httpx.AsyncClient")
    def test_supabase_called_with_correct_headers(self, mock_async_client):
        """Verify Authorization and apikey headers forwarded to Supabase."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            return_value=_mock_httpx_failure(401)
        )
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

        client.get(
            "/brain/career-brain",
            headers={"Authorization": "Bearer my-jwt-token"},
        )

        call_kwargs = mock_client_instance.get.call_args
        headers_sent = call_kwargs[1]["headers"]
        assert headers_sent["Authorization"] == "Bearer my-jwt-token"
        assert headers_sent["apikey"] == "service-key-xyz"


# ===========================================================================
# career_brain_service integration
# ===========================================================================


class TestCareerBrainService:
    def _setup_valid_auth(self, mock_async_client):
        """Configure httpx mock for a valid authenticated user."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            return_value=_mock_httpx_success(VALID_USER_RESPONSE)
        )
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

    @patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-key-xyz",
        },
    )
    @patch("routers.career_brain.career_brain_service")
    @patch("routers.career_brain.httpx.AsyncClient")
    def test_service_exception_returns_500(
        self, mock_async_client, mock_service
    ):
        """career_brain_service.get_career_brain raises → 500."""
        self._setup_valid_auth(mock_async_client)
        mock_service.get_career_brain = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )

        resp = client.get(
            "/brain/career-brain",
            headers={"Authorization": "Bearer valid-jwt"},
        )

        assert resp.status_code == 500
        assert "AI service unavailable" in resp.json()["detail"]

    @patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-key-xyz",
        },
    )
    @patch("routers.career_brain.career_brain_service")
    @patch("routers.career_brain.httpx.AsyncClient")
    def test_happy_path_returns_200_with_career_brain_data(
        self, mock_async_client, mock_service
    ):
        """Valid token + working service → 200 with career brain payload."""
        self._setup_valid_auth(mock_async_client)
        mock_service.get_career_brain = AsyncMock(return_value=CAREER_BRAIN_RESULT)

        resp = client.get(
            "/brain/career-brain",
            headers={"Authorization": "Bearer valid-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["job_readiness_score"] == 78
        assert "Python" in body["skill_analysis"]["strong"]

    @patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-key-xyz",
        },
    )
    @patch("routers.career_brain.career_brain_service")
    @patch("routers.career_brain.httpx.AsyncClient")
    def test_correct_user_id_passed_to_service(
        self, mock_async_client, mock_service
    ):
        """The user_id extracted from JWT is forwarded to the service."""
        self._setup_valid_auth(mock_async_client)
        mock_service.get_career_brain = AsyncMock(return_value=CAREER_BRAIN_RESULT)

        client.get(
            "/brain/career-brain",
            headers={"Authorization": "Bearer valid-jwt"},
        )

        mock_service.get_career_brain.assert_called_once_with("user-xyz-999")

    @patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "anon-key-fallback",  # SERVICE_KEY absent
        },
        clear=True,
    )
    @patch("routers.career_brain.career_brain_service")
    @patch("routers.career_brain.httpx.AsyncClient")
    def test_falls_back_to_anon_key_when_service_key_absent(
        self, mock_async_client, mock_service
    ):
        """When SUPABASE_SERVICE_KEY missing, SUPABASE_ANON_KEY is used."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            return_value=_mock_httpx_success(VALID_USER_RESPONSE)
        )
        mock_async_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_service.get_career_brain = AsyncMock(return_value=CAREER_BRAIN_RESULT)

        resp = client.get(
            
            "/brain/career-brain",
            headers={"Authorization": "Bearer valid-jwt"},
        )

        assert resp.status_code == 200
        # Verify anon key was used in the header
        call_kwargs = mock_client_instance.get.call_args[1]["headers"]
        assert call_kwargs["apikey"] == "anon-key-fallback"