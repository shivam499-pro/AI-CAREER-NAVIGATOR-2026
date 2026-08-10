import pytest
from fastapi.testclient import TestClient
from main import app

pytestmark = pytest.mark.live

client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.integration
class TestInterviewFlowLive:

    def test_generate_questions_live(self, live_test_user, live_auth_headers, live_supabase):
        # /generate-questions requires a profile, so we insert a dummy one first
        live_supabase.table("profiles").upsert({
            "user_id": live_test_user["id"],
            "career_goal": "Full Stack Developer",
            "extra_skills": ["Python", "React"]
        }).execute()

        response = client.post(
            "/api/v1/interview/generate-questions",
            json={
                "user_id": live_test_user["id"],
                "career_path": "Full Stack Developer",
                "difficulty": "medium",
                "personality": "professional",
                "interview_mode": "technical",
            },
            headers=live_auth_headers,
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert "questions" in body
        assert len(body["questions"]) > 0
        
        # Verify the question structure has expected fields
        first_question = body["questions"][0]
        assert "question" in first_question
        assert "type" in first_question

    def test_evaluate_answer_live(self, live_test_user, live_auth_headers):
        response = client.post(
            "/api/v1/interview/evaluate-answer",
            json={
                "user_id": live_test_user["id"],
                "question": "Explain the concept of REST APIs.",
                "answer": "REST uses HTTP verbs like GET, POST, PUT, DELETE for stateless communication.",
                "career_path": "Full Stack Developer",
            },
            headers=live_auth_headers,
        )

        assert response.status_code == 200, response.text
        body = response.json()
        
        # Verify evaluation fields
        assert "score" in body
        assert isinstance(body["score"], int) or isinstance(body["score"], float)
        assert "good_points" in body
        assert "missing_points" in body
        assert "model_answer" in body

    def test_save_session_and_history_live(self, live_test_user, live_auth_headers):
        # Step 1: Save a session
        save_response = client.post(
            "/api/v1/interview/save-session",
            json={
                "user_id": live_test_user["id"],
                "career_path": "Backend Engineer",
                "questions": ["What is REST?", "Explain dependency injection."],
                "answers": [
                    {"question": "What is REST?", "answer": "Representational state transfer."},
                    {"question": "Explain dependency injection.", "answer": "Inversion of control pattern."}
                ],
                "scores": [8, 9],
                "total_score": 17,
                "difficulty": "medium",
                "interview_mode": "technical",
                "is_simulation": False,
                "is_voice": False,
            },
            headers=live_auth_headers,
        )

        assert save_response.status_code == 200, save_response.text
        save_body = save_response.json()
        assert save_body.get("success") is True

        # Step 2: Fetch history and verify the session appears
        history_response = client.get(
            f"/api/v1/interview/history/{live_test_user['id']}?page=1&limit=10",
            headers=live_auth_headers,
        )

        assert history_response.status_code == 200, history_response.text
        history_body = history_response.json()
        
        assert "sessions" in history_body
        sessions = history_body["sessions"]
        assert len(sessions) > 0, "Saved session did not appear in history"
        
        # Check that the saved session is the one we just inserted
        latest_session = sessions[0]
        assert latest_session["career_path"] == "Backend Engineer"
        assert latest_session["total_score"] == 17
