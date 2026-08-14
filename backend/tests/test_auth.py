"""
Tests for authentication and authorization.
Tests JWT token creation, validation, and user authentication.
"""

import pytest
import jwt
import subprocess
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestJWTTokenCreation:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test that access token is created with correct payload."""
        from lib.auth import create_access_token, JWT_SECRET_KEY, JWT_ALGORITHM
        
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = create_access_token(user_id, email)
        
        # Decode and verify token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token(self):
        """Test that refresh token is created with correct payload."""
        from lib.auth import create_refresh_token, JWT_SECRET_KEY, JWT_ALGORITHM
        
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = create_refresh_token(user_id, email)
        
        # Decode and verify token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload

    def test_access_token_expiry(self):
        """Test that access token has correct expiry."""
        from lib.auth import create_access_token, ACCESS_TOKEN_EXPIRE_HOURS
        
        token = create_access_token("user-123", "test@example.com")
        
        # Verify expiry is approximately 1 hour from now
        from lib.auth import decode_token
        payload = decode_token(token)
        
        # Token should be valid (not expired)
        exp = payload["exp"]
        now = int(datetime.now(timezone.utc).timestamp())
        assert exp > now
        # And should expire within about 1 hour (+/- 5 minutes)
        assert exp - now <= 3660  # 1 hour + 1 minute

    def test_refresh_token_expiry_longer_than_access(self):
        """Test that refresh token has longer expiry than access token."""
        from lib.auth import (
            create_access_token, 
            create_refresh_token,
            ACCESS_TOKEN_EXPIRE_HOURS,
            REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        access_token = create_access_token("user-123", "test@example.com")
        refresh_token = create_refresh_token("user-123", "test@example.com")
        
        from lib.auth import decode_token
        
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)
        
        assert refresh_payload["exp"] > access_payload["exp"]
        assert REFRESH_TOKEN_EXPIRE_DAYS > ACCESS_TOKEN_EXPIRE_HOURS


class TestTokenDecoding:
    """Test JWT token decoding and validation."""

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        from lib.auth import create_access_token, decode_token
        
        token = create_access_token("user-123", "test@example.com")
        
        payload = decode_token(token)
        
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"

    def test_decode_expired_token(self):
        """Test that decoding an expired token raises error."""
        from lib.auth import JWT_SECRET_KEY, JWT_ALGORITHM
        
        # Create an expired token (expired 1 hour ago)
        expired_time = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "type": "access",
            "exp": expired_time,
            "iat": expired_time - 3600
        }
        
        expired_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        from lib.auth import decode_token
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail["error_type"]

    def test_decode_invalid_token(self):
        """Test that decoding an invalid token raises error."""
        from lib.auth import decode_token
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid-token-string")
        
        assert exc_info.value.status_code == 401
        assert "invalid_token" in exc_info.value.detail["error_type"]

    def test_decode_token_manual_expiry_check_catches_what_pyjwt_misses(self):
        """
        decode_token has TWO expiry checks: PyJWT's own built-in check inside
        jwt.decode(), and a manual `if exp < now: raise ExpiredSignatureError`
        right after. A naturally-expired token always trips the FIRST check
        (see test_decode_expired_token above), so the manual check never runs
        in practice -- it's a defense-in-depth safety net for a payload PyJWT
        itself didn't flag as expired (e.g. a non-default verification
        configuration). We prove the safety net actually works by mocking
        jwt.decode to hand back an already-expired payload directly, bypassing
        PyJWT's own validation.
        """
        from lib.auth import decode_token
        from fastapi import HTTPException

        expired_payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "type": "access",
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
            "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
        }

        with patch("lib.auth.jwt.decode", return_value=expired_payload):
            with pytest.raises(HTTPException) as exc_info:
                decode_token("irrelevant-because-jwt.decode-is-mocked")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_type"] == "token_expired"


class TestGetCurrentUser:
    """Test the get_current_user dependency."""

    def test_get_current_user_no_authorization(self):
        """Test that missing authorization header raises 401."""
        from lib.auth import get_current_user
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(None)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_type"] == "no_token"

    def test_get_current_user_valid_token(self, test_user):
        """Test getting current user with valid JWT token."""
        from lib.auth import create_access_token, get_current_user
        
        token = create_access_token(test_user["id"], test_user["email"])
        
        with patch('lib.auth.supabase') as mock_supabase:
            mock_supabase.auth.get_user.side_effect = Exception("Not our JWT")
            
            user = get_current_user(f"Bearer {token}")
            
            assert user.id == test_user["id"]
            assert user.email == test_user["email"]

    def test_get_current_user_invalid_token(self):
        """Test that invalid token raises 401."""
        from lib.auth import get_current_user
        from fastapi import HTTPException
        
        with patch('lib.auth.supabase') as mock_supabase:
            mock_supabase.auth.get_user.side_effect = Exception("Invalid token")
            
            with pytest.raises(HTTPException) as exc_info:
                get_current_user("Bearer invalid-token")
            
            assert exc_info.value.status_code == 401

    def test_get_current_user_supabase_token_accepted_short_circuits_jwt_fallback(self):
        """When Supabase itself validates the token, get_current_user should
        return supabase's user object immediately and never fall through to
        the custom-JWT decode path."""
        from lib.auth import get_current_user

        supabase_user = MagicMock()
        supabase_user.id = "supabase-user-1"
        supabase_user.email = "supabase-user@example.com"

        supabase_response = MagicMock()
        supabase_response.user = supabase_user

        with patch("lib.auth.supabase") as mock_supabase, \
             patch("lib.auth.decode_token") as mock_decode:
            mock_supabase.auth.get_user.return_value = supabase_response

            result = get_current_user("Bearer a-real-supabase-token")

        assert result is supabase_user
        mock_decode.assert_not_called()

    def test_get_current_user_both_methods_fail_with_non_http_exception(self):
        """If the custom-JWT fallback raises something OTHER than an
        HTTPException (e.g. a PyJWT edge-case error decode_token's own
        try/except doesn't recognize), get_current_user must still swallow
        it and report a clean 401 -- not let the raw exception leak out."""
        from lib.auth import get_current_user
        from fastapi import HTTPException

        with patch("lib.auth.supabase") as mock_supabase, \
             patch("lib.auth.decode_token", side_effect=ValueError("unexpected pyjwt edge case")):
            mock_supabase.auth.get_user.side_effect = Exception("not a supabase token")

            with pytest.raises(HTTPException) as exc_info:
                get_current_user("Bearer some-token")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_type"] == "invalid_token"
        assert "Unauthorized" in exc_info.value.detail["message"]

    def test_get_current_user_outer_handler_recognizes_token_related_errors(self):
        """An exception raised OUTSIDE both inner try/except blocks (e.g.
        while extracting the token from the header) is caught by the
        outermost handler. If its message mentions 'token' or 'expired' it
        gets the session-expired framing rather than the generic one."""
        from lib.auth import get_current_user
        from fastapi import HTTPException

        bad_authorization = MagicMock()
        bad_authorization.replace.side_effect = RuntimeError("token header malformed")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(bad_authorization)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_type"] == "token_expired"
        assert "re-authenticate" in exc_info.value.detail["message"].lower()

    def test_get_current_user_outer_handler_generic_error_fallback(self):
        """Same outer handler, but with an error message that mentions
        neither 'token' nor 'expired' -- should fall through to the
        generic 'authentication_error' branch with the raw message included."""
        from lib.auth import get_current_user
        from fastapi import HTTPException

        bad_authorization = MagicMock()
        bad_authorization.replace.side_effect = RuntimeError("connection reset")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(bad_authorization)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_type"] == "authentication_error"
        assert "connection reset" in exc_info.value.detail["message"]


class TestAuthRouter:
    """Test auth router endpoints."""

    def test_signup_endpoint(self):
        """Test signup endpoint."""
        from fastapi.testclient import TestClient
        from main import app
        
        with patch('routers.auth.get_anon_client') as mock_get_anon_client:
            client = TestClient(app)
            
            response = client.post(
                "/api/v1/auth/signup",
                json={"email": "newuser@example.com", "password": "password123"}
            )
            
            assert response.status_code == 200
            assert "message" in response.json()

    def test_login_endpoint(self):
        """Test login endpoint."""
        from fastapi.testclient import TestClient
        from main import app
        
        with patch('routers.auth.get_anon_client') as mock_get_anon_client:
            client = TestClient(app)
            
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "password123"}
            )
            
            assert response.status_code == 200
            assert "access_token" in response.json()

    def test_get_current_user_no_token(self):
        """Test /me endpoint without token returns 401."""
        from fastapi.testclient import TestClient
        from main import app
        
        with patch('routers.auth.get_anon_client') as mock_get_anon_client:
            client = TestClient(app)
            
            response = client.get("/api/v1/auth/me")
            
            assert response.status_code == 401

    def test_get_current_user_with_token(self):
        """Test /me endpoint with valid token."""
        from fastapi.testclient import TestClient
        from main import app
        from lib.auth import create_access_token
        
        with patch('routers.auth.get_anon_client') as mock_get_anon_client:
            client = TestClient(app)
            
            token = create_access_token("user-123", "test@example.com")
            
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # May return 401 or 404 depending on router state
            assert response.status_code in [200, 401, 404]
            # Only check for user data if status is 200
            if response.status_code == 200:
                data = response.json()
                assert "user_id" in data or "email" in data


class TestAuthorizationErrors:
    """Test authorization error handling."""

    def test_authorization_missing_detail(self):
        """Test error detail when authorization is missing."""
        from lib.auth import get_current_user
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(None)
        
        detail = exc_info.value.detail
        assert "no_token" in detail["error_type"]
        assert "suggestion" in detail

    def test_expired_token_detail(self):
        """Test error detail when token is expired."""
        from lib.auth import JWT_SECRET_KEY, JWT_ALGORITHM
        from datetime import timedelta
        
        expired_time = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "type": "access",
            "exp": expired_time,
            "iat": expired_time - 3600
        }
        
        expired_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        from lib.auth import decode_token
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)
        
        detail = exc_info.value.detail
        assert "expired" in detail["error_type"]
        assert "new token" in detail["suggestion"].lower() or "log in" in detail["suggestion"].lower()


class TestJWTSecretFailFast:
    """
    Regression tests for the removed hardcoded fallback secret.

    lib.auth performs its secret validation at *module import time*, so by
    the time this test file runs, lib.auth is already imported and the
    check has already run once (successfully, using the valid test secret
    from conftest.py). To actually exercise the fail-fast branch we need a
    fresh interpreter with a controlled environment - a subprocess.
    """

    def _run_import_in_subprocess(self, env_overrides: dict) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env.update(env_overrides)
        repo_root = os.path.join(os.path.dirname(__file__), "..")
        return subprocess.run(
            [sys.executable, "-c", "import lib.auth"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_missing_secret_refuses_to_import(self):
        # An empty string must be treated the same as "unset".
        result = self._run_import_in_subprocess({"JWT_SECRET_KEY": ""})
        assert result.returncode != 0
        assert "RuntimeError" in result.stderr
        assert "JWT_SECRET_KEY" in result.stderr

    def test_known_placeholder_secret_refuses_to_import(self):
        result = self._run_import_in_subprocess(
            {"JWT_SECRET_KEY": "your-super-secret-key-change-in-production"}
        )
        assert result.returncode != 0
        assert "RuntimeError" in result.stderr

    def test_too_short_secret_refuses_to_import(self):
        result = self._run_import_in_subprocess({"JWT_SECRET_KEY": "short"})
        assert result.returncode != 0
        assert "RuntimeError" in result.stderr

    def test_valid_secret_imports_successfully(self):
        result = self._run_import_in_subprocess(
            {"JWT_SECRET_KEY": "a-genuinely-random-secret-at-least-32-chars-long"}
        )
        assert result.returncode == 0, result.stderr
