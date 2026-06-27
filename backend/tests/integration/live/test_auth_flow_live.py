"""
Live Auth Flow Tests
Tests the complete auth flow against real Supabase.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.integration
class TestAuthFlowLive:
 
    def test_real_supabase_token_is_accepted_on_protected_endpoint(
        self, live_auth_headers, live_test_user
    ):
        response = client.get("/api/v1/profile/me", headers=live_auth_headers)
 
        # A brand-new user has no profile row yet, so 200 (empty) or 404
        # are both correct — what matters is NOT 401.
        assert response.status_code != 401, (
            f"Real Supabase token was rejected. Response: {response.text}"
        )
        assert response.status_code in (200, 404)
 
    def test_request_without_token_is_rejected(self):
        """Sanity check: the live server still rejects unauthenticated requests."""
        response = client.get("/api/v1/profile/me")
        assert response.status_code == 401

    def test_login_returns_valid_token(self, live_supabase):
        """Login with valid credentials returns usable token."""
        # This test requires a pre-existing test account in your test project
        # Set TEST_USER_EMAIL and TEST_USER_PASSWORD in .env.test
        import os
        email = os.getenv("TEST_USER_EMAIL")
        password = os.getenv("TEST_USER_PASSWORD")
        
        if not email or not password:
            pytest.skip("TEST_USER_EMAIL and TEST_USER_PASSWORD not set in .env.test")
        
        response = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        
        assert response.status_code == 200
        body = response.json()
        token = body.get("access_token")
        assert token is not None
        
        # Verify token works by calling an authenticated endpoint
        profile_response = client.get(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_response.status_code in (200, 404)  # 404 = no profile yet, but auth worked