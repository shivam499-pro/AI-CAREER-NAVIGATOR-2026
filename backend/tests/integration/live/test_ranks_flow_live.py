"""
Live tests for routers/ranks.py — real Supabase, real HTTP, no mocks.

@pytest.mark.integration is required: tests/conftest.py's autouse
mock_supabase_singleton fixture force-mocks core.supabase_client for
every test EXCEPT ones carrying this marker. Without it, these would
silently run against a mock instead of the real TEST Supabase project.
"""
import pytest
from main import app
from fastapi.testclient import TestClient

pytestmark = pytest.mark.live

client = TestClient(app)


@pytest.mark.integration
class TestRanksFlowLive:

    def test_get_rank_rejects_request_with_no_token(self, live_test_user):
        response = client.get(f"/api/v1/ranks/{live_test_user['id']}")
        assert response.status_code == 401

    def test_get_rank_rejects_request_for_another_users_id(self, live_auth_headers):
        response = client.get("/api/v1/ranks/some-other-users-uuid", headers=live_auth_headers)
        assert response.status_code == 403

    def test_get_own_rank_succeeds(self, live_test_user, live_auth_headers):
        response = client.get(f"/api/v1/ranks/{live_test_user['id']}", headers=live_auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["xp"] == 0
        assert body["level"] == 1

    def test_update_rank_rejects_request_with_no_token(self):
        response = client.post("/api/v1/ranks/update", json={"score": 90})
        assert response.status_code == 401

    def test_update_rank_ignores_spoofed_user_id_and_updates_caller_only(self, live_test_user, live_auth_headers):
        response = client.post(
            "/api/v1/ranks/update",
            json={"user_id": "some-other-real-or-fake-uuid", "score": 90},
            headers=live_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["xp"] == 50

        follow_up = client.get(f"/api/v1/ranks/{live_test_user['id']}", headers=live_auth_headers)
        assert follow_up.status_code == 200
        assert follow_up.json()["xp"] == 50