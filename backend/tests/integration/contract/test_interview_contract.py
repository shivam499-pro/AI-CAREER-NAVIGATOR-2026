"""
Interview Contract Tests
useInterviewSession.ts makes 3 critical API calls.
Each has a specific response shape the hook depends on.
"""
import pytest
from unittest.mock import patch, MagicMock
from tests.integration.conftest import TEST_USER_ID, authed_client, make_supabase_response

class TestInterviewContract:

    def test_generate_questions_returns_questions_array(self, authed_client, mock_supabase):
        """
        useInterviewSession.startInterview() checks:
        if (!data.questions?.length) throw new Error('No questions returned')
        
        Shape must be: { questions: Question[] }
        """
        mock_questions = [
            {
                "id": 1,
                "question": "Explain REST vs GraphQL",
                "type": "technical",
                "difficulty": "medium",
                "hint": "Think about query flexibility"
            }
        ]
        
        with patch("services.gemini_service.generate_interview_questions") as mock_gen:
            mock_gen.return_value = mock_questions
            
            response = authed_client.post(
                "/api/v1/interview/generate-questions",
                json={
                    "user_id": TEST_USER_ID,
                    "career_path": "Full Stack Developer",
                    "difficulty": "medium",
                    "personality": "friendly",
                    "interview_mode": "technical"
                }
            )
        # ADD this patch alongside the existing mock_gen patch:
        with patch("routers.interview.interview_module_service.prepare_interview_profile") as mock_profile, \
            patch("services.gemini_service.generate_interview_questions") as mock_gen:
            mock_profile.return_value = {"user_id": TEST_USER_ID, "resume_text": "test resume"}
            mock_gen.return_value = mock_questions
    
            response = authed_client.post(
                "/api/v1/interview/generate-questions",
                json={
                    "user_id": TEST_USER_ID,
                    "career_path": "Full Stack Developer",
                    "difficulty": "medium",
                    "personality": "friendly",
                    "interview_mode": "technical"
                }
            )
        
        assert response.status_code == 200
        body = response.json()
        assert "questions" in body, "questions array missing — startInterview will throw"
        assert isinstance(body["questions"], list)
        assert len(body["questions"]) > 0

    def test_evaluate_answer_returns_required_feedback_fields(self, authed_client, mock_supabase):
        """
        evaluateAndAdvance() accesses:
        feedback.score, feedback.good_points, feedback.missing_points,
        feedback.model_answer, feedback.tip
        
        Missing fields cause undefined errors in ResultsScreen.
        """
        mock_feedback = {
            "score": 7,
            "good_points": ["Good explanation of REST principles"],
            "missing_points": ["Didn't mention caching"],
            "model_answer": "REST is stateless, GraphQL is flexible...",
            "tip": "Mention tradeoffs next time"
        }
        
        with patch("services.gemini_service.evaluate_interview_answer") as mock_eval:
            mock_eval.return_value = mock_feedback
            
            response = authed_client.post(
                "/api/v1/interview/evaluate-answer",
                json={
                    "question": "Explain REST vs GraphQL",
                    "answer": "REST uses fixed endpoints...",
                    "career_path": "Full Stack Developer",
                    "user_id": TEST_USER_ID,
                }
            )
        
        assert response.status_code == 200
        body = response.json()
        
        required_fields = ["score", "good_points", "missing_points", "model_answer", "tip"]
        for field in required_fields:
            assert field in body, f"feedback.{field} missing — ResultsScreen will break"

    def test_save_session_returns_badge_and_xp_fields(self, authed_client, mock_supabase):
        """
        finishInterview() toasts on:
        if (sessionData.new_badges?.length > 0) → show badge toast
        if (sessionData.total_xp_earned > 0) → show XP toast
        
        These fields must be present (can be empty/0).
        """
        mock_supabase.table.return_value.upsert.return_value\
            .execute.return_value = make_supabase_response([{"id": "session-1"}])
        
        with patch("services.badge_service.check_and_award_badges") as mock_badges:
            mock_badges.return_value = {"newly_earned": [], "xp_awarded": 50}
            
            response = authed_client.post(
                "/api/v1/interview/save-session",
                json={
                    "user_id": TEST_USER_ID,
                    "career_path": "Full Stack Developer",
                    "questions": ["Q1", "Q2"],
                    "answers": [{"question": "Q1", "answer": "A1"}],
                    "scores": [7, 8],
                    "total_score": 15,
                    "difficulty": "medium",
                    "interview_mode": "technical",
                    "is_simulation": False,
                    "is_voice": False,
                }
            )
        
        assert response.status_code == 200
        body = response.json()
        # Frontend checks these — must exist even if empty
        assert "new_badges" in body or "newly_earned" in body, \
            "Badge field missing — toast logic will error"

    def test_missing_required_fields_returns_422(self, authed_client):
        """
        FastAPI validates request bodies. Missing required fields = 422.
        Frontend should handle this (currently doesn't always check).
        """
        response = authed_client.post(
            "/api/v1/interview/generate-questions",
            json={}  # Missing all required fields
        )
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body  # FastAPI validation error shape
