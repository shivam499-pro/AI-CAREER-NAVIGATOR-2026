
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.integration
class TestBadgeAwardFlowLive:

    def test_first_session_awards_badge(self, live_test_user, live_auth_headers, live_supabase):
        
        session_response = client.post(
            "/api/v1/interview/save-session",
            json={
                "user_id": live_test_user["id"],
                "career_path": "Full Stack Developer",
                "questions": ["What is REST?"],
                "answers": [{"question": "What is REST?", "answer": "REST is..."}],
                "scores": [7],
                "total_score": 7,
                "difficulty": "medium",
                "interview_mode": "technical",
                "is_simulation": False,
                "is_voice": False,
            },
            headers=live_auth_headers,
        )

        assert session_response.status_code == 200, session_response.text

        badges_response = client.get(
            f"/api/v1/badges/{live_test_user['id']}", headers=live_auth_headers
        )
        assert badges_response.status_code == 200, badges_response.text
        badges_body = badges_response.json()

        earned_ids = [b["badge_id"] for b in badges_body.get("earned", [])]
        assert "first_session" in earned_ids, (
            "first_session badge was not awarded after first interview session. "
            f"Earned badges were: {earned_ids}"
        )

    def test_badge_service_called_directly_awards_and_persists(self, live_test_user, live_supabase):
        
        from services.badge_service import check_and_award_badges

        result = check_and_award_badges(
            user_id=live_test_user["id"],
            event="session_complete",
            event_data={"score": 7, "career_path": "Full Stack Developer"},
        )

        assert result is not None

        rows = (
            live_supabase.table("user_badges")
            .select("*")
            .eq("user_id", live_test_user["id"])
            .execute()
        )
        assert len(rows.data) > 0, "check_and_award_badges did not write any badge rows"

    def test_streak_updates_after_session(self, live_test_user, live_auth_headers):
        response = client.post(
            "/api/v1/streaks/update", json={}, headers=live_auth_headers
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert "current_streak" in body
        assert body["current_streak"] >= 1
        assert "total_sessions" in body

    def test_get_streak_reflects_update(self, live_test_user, live_auth_headers):
        
        update_response = client.post(
            "/api/v1/streaks/update", json={}, headers=live_auth_headers
        )
        assert update_response.status_code == 200

        get_response = client.get("/api/v1/streaks/", headers=live_auth_headers)
        assert get_response.status_code == 200
        body = get_response.json()
        assert body.get("total_sessions", 0) >= 1