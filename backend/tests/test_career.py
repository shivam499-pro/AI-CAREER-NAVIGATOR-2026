"""
Tests for routers/career.py

Two units under test, deliberately kept separate:
  1. get_current_user  — the auth dependency (token parsing + Supabase verify)
  2. get_career_evolution — the route handler (ownership check + service call + fallback)

NOTE: career.py defines its own get_current_user rather than reusing
core.middleware.get_current_user (which the rest of the app — e.g. badges.py —
depends on). It also calls create_client(...) fresh on every request instead of
reusing a shared client. Both are flagged as refactor candidates in the review;
these tests cover the behavior as currently implemented.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.career import router, get_current_user

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ─── 1. get_current_user — header parsing (no network) ───────────────────────

def test_missing_authorization_header_raises_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=None)
    assert exc.value.status_code == 401
    assert "Missing" in exc.value.detail


def test_malformed_header_without_bearer_prefix_raises_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="Token abc123")
    assert exc.value.status_code == 401
    assert "Invalid authorization header format" in exc.value.detail


def test_empty_bearer_token_still_attempts_verification():
    # "Bearer " with nothing after it should not blow up on the string
    # handling itself — it should fall through to the verify path and fail there.
    with patch("routers.career.supabase_url", "https://x.supabase.co"), \
         patch("routers.career.supabase_key", "key"), \
         patch("routers.career.create_client") as mock_create:
        mock_client = MagicMock()
        mock_client.auth.get_user.side_effect = Exception("invalid jwt")
        mock_create.return_value = mock_client

        with pytest.raises(HTTPException) as exc:
            get_current_user(authorization="Bearer ")
        assert exc.value.status_code == 401


# ─── 2. get_current_user — server configuration ───────────────────────────────

def test_missing_supabase_config_raises_500():
    with patch("routers.career.supabase_url", None), \
         patch("routers.career.supabase_key", None):
        with pytest.raises(HTTPException) as exc:
            get_current_user(authorization="Bearer sometoken")
        assert exc.value.status_code == 500
        assert "Server configuration error" in exc.value.detail


def test_missing_only_supabase_key_raises_500():
    with patch("routers.career.supabase_url", "https://x.supabase.co"), \
         patch("routers.career.supabase_key", None):
        with pytest.raises(HTTPException) as exc:
            get_current_user(authorization="Bearer sometoken")
        assert exc.value.status_code == 500


# ─── 3. get_current_user — token verification outcomes ────────────────────────

def test_valid_token_returns_user_id():
    with patch("routers.career.supabase_url", "https://x.supabase.co"), \
         patch("routers.career.supabase_key", "key"), \
         patch("routers.career.create_client") as mock_create:
        mock_user = MagicMock()
        mock_user.id = "user-abc-123"
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_response
        mock_create.return_value = mock_client

        result = get_current_user(authorization="Bearer validtoken")
        assert result == "user-abc-123"
        # Confirms the "Bearer " prefix is stripped before verification
        mock_client.auth.get_user.assert_called_once_with("validtoken")


def test_token_verification_returns_no_user_raises_401():
    with patch("routers.career.supabase_url", "https://x.supabase.co"), \
         patch("routers.career.supabase_key", "key"), \
         patch("routers.career.create_client") as mock_create:
        mock_response = MagicMock()
        mock_response.user = None
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_response
        mock_create.return_value = mock_client

        with pytest.raises(HTTPException) as exc:
            get_current_user(authorization="Bearer expiredtoken")
        assert exc.value.status_code == 401
        assert "Invalid or expired token" in exc.value.detail


def test_supabase_raises_generic_exception_is_swallowed_as_401():
    # Any unexpected Supabase-side error (network blip, malformed JWT, etc.)
    # must not leak as a 500 — it should collapse to 401.
    with patch("routers.career.supabase_url", "https://x.supabase.co"), \
         patch("routers.career.supabase_key", "key"), \
         patch("routers.career.create_client") as mock_create:
        mock_client = MagicMock()
        mock_client.auth.get_user.side_effect = ValueError("jwt malformed")
        mock_create.return_value = mock_client

        with pytest.raises(HTTPException) as exc:
            get_current_user(authorization="Bearer garbage")
        assert exc.value.status_code == 401


def test_internal_500_config_error_is_not_downgraded_to_401():
    # Regression guard: the bare `except Exception` must not catch the
    # HTTPException(500) raised for missing config and remap it to 401.
    # (It's already protected by `except HTTPException: raise` above it —
    # this test locks that ordering in place.)
    with patch("routers.career.supabase_url", None), \
         patch("routers.career.supabase_key", None):
        with pytest.raises(HTTPException) as exc:
            get_current_user(authorization="Bearer sometoken")
        assert exc.value.status_code == 500


# ─── 4. GET /evolution/{user_id} — ownership boundary (the IDOR check) ────────

def _override_user(user_id: str):
    def _fn():
        return user_id
    return _fn


def test_requesting_another_users_evolution_returns_403():
    app.dependency_overrides[get_current_user] = _override_user("user-A")
    try:
        resp = client.get("/evolution/user-B")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_requesting_own_evolution_is_allowed_through_to_service():
    app.dependency_overrides[get_current_user] = _override_user("user-A")
    try:
        with patch("services.career_evolution_engine.get_user_evolution_profile") as mock_profile:
            mock_profile.return_value = {
                "user_id": "user-A",
                "career_paths": [],
                "overall_growth_state": "stagnating",
            }
            resp = client.get("/evolution/user-A")
            assert resp.status_code == 200
            assert resp.json()["user_id"] == "user-A"
            mock_profile.assert_called_once_with("user-A")
    finally:
        app.dependency_overrides.clear()


# ─── 5. GET /evolution/{user_id} — service success + failure paths ────────────

def test_evolution_success_returns_service_payload_verbatim():
    app.dependency_overrides[get_current_user] = _override_user("user-A")
    try:
        payload = {
            "user_id": "user-A",
            "career_paths": [
                {
                    "career_path": "AI/ML Engineer",
                    "avg_score": 72,
                    "trend": "improving",
                    "volatility": 0.12,
                    "total_sessions": 8,
                    "confidence": 0.81,
                }
            ],
            "overall_growth_state": "growing",
        }
        with patch("services.career_evolution_engine.get_user_evolution_profile") as mock_profile:
            mock_profile.return_value = payload
            resp = client.get("/evolution/user-A")
            assert resp.status_code == 200
            assert resp.json() == payload
    finally:
        app.dependency_overrides.clear()


def test_evolution_service_exception_falls_back_gracefully():
    # The handler must never surface a raw 500 for a downstream service error —
    # it should degrade to the documented fallback profile.
    app.dependency_overrides[get_current_user] = _override_user("user-A")
    try:
        with patch("services.career_evolution_engine.get_user_evolution_profile") as mock_profile:
            mock_profile.side_effect = Exception("supabase timeout")
            resp = client.get("/evolution/user-A")
            assert resp.status_code == 200
            body = resp.json()
            assert body == {
                "user_id": "user-A",
                "career_paths": [],
                "overall_growth_state": "stagnating",
            }
    finally:
        app.dependency_overrides.clear()


def test_evolution_import_error_also_falls_back():
    # Covers the `from services import career_evolution_engine` import happening
    # inside the try block — if that ever breaks, it must still fall back, not 500.
    app.dependency_overrides[get_current_user] = _override_user("user-A")
    try:
        with patch.dict("sys.modules", {"services.career_evolution_engine": None}):
            resp = client.get("/evolution/user-A")
            assert resp.status_code == 200
            assert resp.json()["overall_growth_state"] == "stagnating"
    finally:
        app.dependency_overrides.clear()