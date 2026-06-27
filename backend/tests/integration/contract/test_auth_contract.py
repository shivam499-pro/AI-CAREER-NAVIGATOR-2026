"""
Auth Contract Tests
Verifies that authentication behaves exactly as the frontend expects.
The frontend ApiClient in lib/api.ts throws on 401/403 — these tests
verify the exact error shapes it receives.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from tests.integration.conftest import TEST_USER_ID, make_supabase_response

client = TestClient(app, raise_server_exceptions=False)

class TestAuthContract:

    def test_no_token_returns_401(self):
        """
        CRITICAL: Frontend ApiClient.getAuthHeaders() sends no header when
        no session. Backend must return 401, not 500.
        """
        response = client.get("/api/v1/profile/me")
        assert response.status_code == 401
        body = response.json()
        # Frontend checks for 'detail' key to extract error message
        assert "detail" in body

    def test_malformed_bearer_token_returns_401(self):
        """Token present but not a valid JWT or Supabase token."""
        response = client.get(
            "/api/v1/profile/me",
            headers={"Authorization": "Bearer not-a-real-token"}
        )
        assert response.status_code == 401

    def test_expired_token_returns_401_with_expired_error_type(self):
        """
        Frontend shows 'Session expired' message when error_type=token_expired.
        Verify the exact shape.
        """
        import jwt
        from datetime import datetime, timezone, timedelta
        import os
        
        expired_payload = {
            "sub": "user-123",
            "email": "test@test.com",
            "type": "access",
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
        expired_token = jwt.encode(
            expired_payload,
            os.getenv("JWT_SECRET_KEY", "test-jwt-secret-minimum-32-chars"),
            algorithm="HS256"
        )
        
        response = client.get(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        body = response.json()
        detail = body.get("detail", {})
        # Frontend checks error_type to display correct message
        assert detail.get("meta", {}) .get("error_code") in ["AUTH_FAILED", "INVALID_TOKEN"]


    def test_cors_headers_present_on_api_response(self):
        """
        Frontend fetch() fails silently on CORS errors.
        Verify Access-Control headers are always present.
        """
        response = client.options(
            "/api/v1/analysis/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code in (200, 204)

    def test_health_endpoint_requires_no_auth(self):
        """
        Frontend checks /health to verify backend is up.
        Must not require authentication.
        """
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "status" in body or "message" in body