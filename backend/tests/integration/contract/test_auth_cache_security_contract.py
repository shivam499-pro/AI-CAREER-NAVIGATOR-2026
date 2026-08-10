"""
Auth Cache Security Contract Tests

End-to-end proof that the cache-key fix in core/middleware.py's JWTVerifier
actually holds when requests flow through the real FastAPI app and router
stack — not just in isolation with _verify_supabase_token mocked away
(that's already covered by tests/test_middleware_components.py's
TestVerifyToken class).

These tests hit a real protected endpoint (GET /api/v1/streaks/) that uses
core.middleware.get_current_user via Depends(), with only the outbound
Supabase HTTP call mocked (not the verification function itself).

WHY streaks:
  - Uses get_current_user from core.middleware (not lib.auth).
  - Uses get_supabase() from core.supabase_client (patched via mock_supabase
    fixture), not a module-level create_client() one-off.
  - Returns user-scoped data, so we can assert the correct user_id was used.
"""
import hashlib
import base64
import json as json_module

import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from core.middleware import jwt_verifier
from core.cache import cache
from tests.integration.conftest import make_supabase_response


# ── Helpers ──────────────────────────────────────────────────────────────────

REAL_USER_ID = "real-user-cache-sec-001"
REAL_USER_EMAIL = "real-user@careernav.test"

ATTACKER_USER_ID = "attacker-cache-sec-999"


def _make_unsigned_jwt(payload: dict) -> str:
    """Build a structurally valid 3-part JWT (header.payload.signature)
    with no cryptographic validity — used to craft forged tokens."""
    def _b64(obj):
        raw = json_module.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    return f"{_b64({'alg': 'HS256', 'typ': 'JWT'})}.{_b64(payload)}.nosig"


def _supabase_user_response(user_id: str, email: str) -> dict:
    """The JSON shape returned by Supabase's GET /auth/v1/user on success."""
    return {
        "id": user_id,
        "email": email,
        "user_metadata": {"role": "user"},
    }


# ── Test class ───────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestAuthCacheSecurityContract:
    """End-to-end tests proving the cache-key security fix holds through
    the real app's request lifecycle."""

    @pytest.fixture(autouse=True)
    def _clear_jwt_cache(self):
        """Ensure no stale cache entries leak between tests."""
        cache._memory_cache.clear()
        cache._memory_expiry.clear()
        yield
        cache._memory_cache.clear()
        cache._memory_expiry.clear()

    @pytest.fixture
    def raw_client(self):
        """A TestClient with NO dependency overrides — we want the REAL
        get_current_user path to execute, just with the Supabase HTTP
        call intercepted at the httpx level."""
        app.dependency_overrides.clear()
        client = TestClient(app, raise_server_exceptions=False)
        yield client
        app.dependency_overrides.clear()

    # ── 1. Valid token → 200, correct user-scoped data ───────────────────

    def test_valid_token_returns_200_with_user_scoped_data(
        self, raw_client, mock_supabase
    ):
        """A token that passes Supabase verification should yield 200
        and the streak data should be scoped to the verified user_id."""
        token = _make_unsigned_jwt({"sub": REAL_USER_ID, "email": REAL_USER_EMAIL})

        # Mock the Supabase /auth/v1/user HTTP call to return success.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _supabase_user_response(
            REAL_USER_ID, REAL_USER_EMAIL
        )

        # Provide streak data for the user.
        mock_supabase.table.return_value.select.return_value \
            .eq.return_value.execute.return_value = make_supabase_response([{
                "user_id": REAL_USER_ID,
                "current_streak": 5,
                "longest_streak": 10,
                "last_practice_date": "2026-07-24",
                "total_sessions": 42,
            }])

        with patch("core.middleware.httpx.AsyncClient") as MockAsyncClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockAsyncClient.return_value = mock_client_instance

            response = raw_client.get(
                "/api/v1/streaks/",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200, (
            f"Expected 200 for a valid token, got {response.status_code}: "
            f"{response.text}"
        )
        body = response.json()
        assert body["current_streak"] == 5
        assert body["total_sessions"] == 42

    # ── 2. Forged token cannot ride on a real user's cache ───────────────

    def test_forged_token_after_real_request_gets_401(
        self, raw_client, mock_supabase
    ):
        """SECURITY: After a legitimate user authenticates (populating the
        cache), an attacker who crafts a token with the same 'sub' claim
        but a different signature must still get 401. This proves the
        cache is keyed by the verified token hash, not by unverified
        claims."""
        real_token = _make_unsigned_jwt({
            "sub": REAL_USER_ID, "email": REAL_USER_EMAIL
        })

        # ── Step 1: legitimate request by the real user ──────────────────
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = _supabase_user_response(
            REAL_USER_ID, REAL_USER_EMAIL
        )

        mock_supabase.table.return_value.select.return_value \
            .eq.return_value.execute.return_value = make_supabase_response([{
                "user_id": REAL_USER_ID,
                "current_streak": 3,
                "longest_streak": 7,
                "last_practice_date": "2026-07-24",
                "total_sessions": 20,
            }])

        with patch("core.middleware.httpx.AsyncClient") as MockAsyncClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response_ok
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockAsyncClient.return_value = mock_client_instance

            legit_response = raw_client.get(
                "/api/v1/streaks/",
                headers={"Authorization": f"Bearer {real_token}"},
            )

        assert legit_response.status_code == 200, (
            "Prerequisite failed: the real user's request should succeed"
        )

        # Verify the real token's result is now cached.
        real_cache_key = jwt_verifier._token_cache_key(real_token)
        assert cache.get(real_cache_key) is not None, (
            "Cache should contain the verified result for the real token"
        )

        # ── Step 2: attacker sends a DIFFERENT token claiming same sub ───
        forged_token = _make_unsigned_jwt({
            "sub": REAL_USER_ID,
            "email": "attacker@evil.com",
            "iat": 9999999999,  # different payload → different token
        })
        assert forged_token != real_token

        # The forged token must NOT get a cache hit (different hash).
        forged_cache_key = jwt_verifier._token_cache_key(forged_token)
        assert forged_cache_key != real_cache_key, (
            "Forged and real tokens must produce different cache keys"
        )
        assert cache.get(forged_cache_key) is None, (
            "Forged token should have no cache entry"
        )

        # Supabase rejects the forged token (invalid signature).
        mock_response_reject = MagicMock()
        mock_response_reject.status_code = 401
        mock_response_reject.json.return_value = {"error": "invalid JWT"}

        with patch("core.middleware.httpx.AsyncClient") as MockAsyncClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response_reject
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockAsyncClient.return_value = mock_client_instance

            forged_response = raw_client.get(
                "/api/v1/streaks/",
                headers={"Authorization": f"Bearer {forged_token}"},
            )

        assert forged_response.status_code == 401, (
            f"SECURITY FAILURE: forged token should be rejected but got "
            f"{forged_response.status_code}. The cache-key fix may have "
            f"regressed — the forged token rode on the real user's cache entry."
        )

    # ── 3. No Authorization header → 401 ─────────────────────────────────

    def test_no_auth_header_returns_401(self, raw_client):
        """A request with no Authorization header must be rejected."""
        response = raw_client.get("/api/v1/streaks/")
        assert response.status_code == 401
        body = response.json()
        assert "detail" in body

    # ── 4. Expired / garbage token → 401 ─────────────────────────────────

    def test_garbage_token_returns_401(self, raw_client, mock_supabase):
        """A completely invalid token string must be rejected."""
        mock_response_reject = MagicMock()
        mock_response_reject.status_code = 401
        mock_response_reject.json.return_value = {"error": "invalid JWT"}

        with patch("core.middleware.httpx.AsyncClient") as MockAsyncClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response_reject
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockAsyncClient.return_value = mock_client_instance

            response = raw_client.get(
                "/api/v1/streaks/",
                headers={"Authorization": "Bearer this-is-total-garbage"},
            )

        assert response.status_code == 401

    def test_expired_token_returns_401(self, raw_client, mock_supabase):
        """A structurally valid but expired token must be rejected by
        Supabase and result in 401."""
        expired_token = _make_unsigned_jwt({
            "sub": REAL_USER_ID,
            "email": REAL_USER_EMAIL,
            "exp": 0,  # expired at epoch
        })

        mock_response_reject = MagicMock()
        mock_response_reject.status_code = 401
        mock_response_reject.json.return_value = {
            "error": "JWT expired",
            "message": "Token has expired",
        }

        with patch("core.middleware.httpx.AsyncClient") as MockAsyncClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response_reject
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockAsyncClient.return_value = mock_client_instance

            response = raw_client.get(
                "/api/v1/streaks/",
                headers={"Authorization": f"Bearer {expired_token}"},
            )

        assert response.status_code == 401
