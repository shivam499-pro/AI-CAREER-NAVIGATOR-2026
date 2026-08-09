"""
Tests for routers/auth.py.

/signup and /login call real Supabase Auth (mocked here at the unit level);
the full end-to-end truth is proven separately against a real Supabase
project in tests/integration/live/test_auth_flow_live.py.

/me delegates entirely to core.middleware.get_current_user — the same
dependency every other authenticated route uses — rather than re-implementing
token parsing here. That's deliberate: a second, router-local auth
implementation is exactly how this router ended up broken in the first place.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from core.middleware import get_current_user, AuthenticatedUser

client = TestClient(app)


def _mock_auth_result(user_id="user-123", email="new@example.com", has_session=True):
    user = MagicMock()
    user.id = user_id
    user.email = email

    session = None
    if has_session:
        session = MagicMock()
        session.access_token = "real-access-token"
        session.refresh_token = "real-refresh-token"
        session.expires_in = 3600

    result = MagicMock()
    result.user = user
    result.session = session
    return result


# ─── POST /signup ───────────────────────────────────────────────────────────

def test_signup_success_returns_tokens_and_user():
    # after
    with patch("routers.auth.get_anon_client") as mock_get_anon_client:
        mock_get_anon_client.return_value.auth.sign_up.return_value = _mock_auth_result()

        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "new@example.com", "password": "hunter2-real-pw"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user-123"
    assert body["access_token"] == "real-access-token"
    assert body["email_confirmation_required"] is False


def test_signup_without_immediate_session_flags_confirmation_required():
    """Supabase returns a user but no session when email confirmation is required."""
    with patch("routers.auth.get_anon_client") as mock_get_anon_client:
        mock_get_anon_client.return_value.auth.sign_up.return_value = _mock_auth_result(has_session=False)

        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "new@example.com", "password": "hunter2-real-pw"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] is None
    assert body["email_confirmation_required"] is True


def test_signup_returns_400_on_supabase_error_without_leaking_details():
    with patch("routers.auth.get_anon_client") as mock_get_anon_client:
        mock_get_anon_client.return_value.auth.sign_up.side_effect = Exception(
            "internal postgres constraint xyz failed"
        )

        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "dupe@example.com", "password": "hunter2-real-pw"},
        )

    assert response.status_code == 400
    assert "postgres" not in response.json()["detail"].lower()


def test_signup_returns_422_when_fields_missing():
    response = client.post("/api/v1/auth/signup", json={"email": "no-password@example.com"})
    assert response.status_code == 422


# ─── POST /login ────────────────────────────────────────────────────────────

def test_login_success_returns_usable_token():
    with patch("routers.auth.get_anon_client") as mock_get_anon_client:
        mock_get_anon_client.return_value.auth.sign_in_with_password.return_value = _mock_auth_result(
            email="existing@example.com"
        )

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "existing@example.com", "password": "correct-password"},
        )

    assert response.status_code == 200
    assert response.json()["access_token"] == "real-access-token"


def test_login_invalid_credentials_returns_401_not_500():
    with patch("routers.auth.get_anon_client") as mock_get_anon_client:
        mock_get_anon_client.return_value.auth.sign_in_with_password.side_effect = Exception(
            "Invalid login credentials"
        )

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "existing@example.com", "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_returns_422_when_fields_missing():
    response = client.post("/api/v1/auth/login", json={"password": "only-password"})
    assert response.status_code == 422


# ─── GET /me ─────────────────────────────────────────────────────────────

def test_get_me_returns_401_with_no_authorization_header():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_me_returns_the_real_authenticated_user():
    fake_user = AuthenticatedUser(user_id="user-456", email="real@example.com", role="user")
    app.dependency_overrides[get_current_user] = lambda: fake_user

    try:
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer some-real-looking-token"}
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user-456"
    assert body["email"] == "real@example.com"

# def test_signup_endpoint(self):
#     """Test signup endpoint."""
#     from unittest.mock import MagicMock, patch
#     from fastapi.testclient import TestClient
#     from main import app

#     with patch('routers.auth.get_anon_client') as mock_get_anon_client:
#         user = MagicMock(id="user-123", email="newuser@example.com")
#         session = MagicMock(access_token="tok", refresh_token="rtok", expires_in=3600)
#         mock_get_anon_client.return_value.auth.sign_up.return_value = MagicMock(user=user, session=session)

#         client = TestClient(app)
#         response = client.post(
#             "/api/v1/auth/signup",
#             json={"email": "newuser@example.com", "password": "password123"}
#         )

#         assert response.status_code == 200
#         assert "message" in response.json()

# def test_login_endpoint(self):
#     """Test login endpoint."""
#     from unittest.mock import MagicMock, patch
#     from fastapi.testclient import TestClient
#     from main import app

#     with patch('routers.auth.get_anon_client') as mock_get_anon_client:
#         user = MagicMock(id="user-123", email="user@example.com")
#         session = MagicMock(access_token="tok", refresh_token="rtok", expires_in=3600)
#         mock_get_anon_client.return_value.auth.sign_in_with_password.return_value = MagicMock(user=user, session=session)

#         client = TestClient(app)
#         response = client.post(
#             "/api/v1/auth/login",
#             json={"email": "user@example.com", "password": "password123"}
#         )

#         assert response.status_code == 200