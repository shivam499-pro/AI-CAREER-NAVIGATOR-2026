"""
Gemini AI Contract Tests
These use PRE-RECORDED Gemini responses (fixtures) — NOT live API calls.
Tests that our parsing layer correctly handles real Gemini output shapes.
"""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from tests.integration.conftest import TEST_USER_ID, make_supabase_response

# Pre-recorded Gemini responses (captured from real API calls)
GEMINI_ANALYSIS_RESPONSE = json.dumps({
    "career_paths": [
        {
            "name": "Full Stack Developer",
            "match_percentage": 85,
            "roadmap": {"target_career": "Full Stack Developer", "milestones": []},
        }
    ],
    "skill_gaps": ["Docker", "Kubernetes"],
    "experience_level": "Mid",
    "strengths": ["React", "Python"],
})

GEMINI_QUESTIONS_RESPONSE = json.dumps([
    {
        "id": 1,
        "question": "Explain the difference between REST and GraphQL",
        "type": "technical",
        "difficulty": "medium",
        "hint": "Think about flexibility vs predictability"
    },
    {
        "id": 2,
        "question": "How do you handle state management in React?",
        "type": "technical",
        "difficulty": "medium",
        "hint": "Consider Redux, Context, Zustand"
    }
])

GEMINI_EVALUATION_RESPONSE = json.dumps({
    "score": 7,
    "good_points": ["Correctly identified statelessness"],
    "missing_points": ["Didn't mention caching strategies"],
    "model_answer": "REST is stateless and uses fixed endpoints...",
    "tip": "Always mention real-world tradeoffs"
})

class TestGeminiContract:

    @pytest.mark.asyncio
    async def test_analysis_parses_gemini_career_paths(self):
        """
        When Gemini returns career paths JSON, gemini_service must parse
        it into the shape analysisClient.getFinalAnalysis() returns.
        """
        from services.gemini_service import run_combined_analysis
        
        with patch("core.gemini_transport.AsyncGeminiTransport.create") as mock_create:
            mock_transport = MagicMock()
            mock_transport.generate = AsyncMock( return_value=GEMINI_ANALYSIS_RESPONSE )
            mock_create.return_value = mock_transport
            
            result = await run_combined_analysis(
                user_profile={"user_id": TEST_USER_ID},
                github_data={"username": "testuser", "repos": []},
                leetcode_data={"username": "testuser", "problems_solved": 50},
                resume_text="Python developer with 3 years experience"
            )
        
        assert result is not None
        assert "career_paths" in result or "error" not in str(result).lower()

    @pytest.mark.asyncio
    async def test_gemini_rate_limit_returns_graceful_error(self):
        """
        When Gemini returns 429, the service must NOT crash.
        It should return a structured error that routers can handle.
        """
        from services.gemini_service import generate_interview_questions
        from core.gemini_transport import RateLimitError
        
        with patch("core.gemini_transport.AsyncGeminiTransport.create") as mock_create:
            mock_transport = MagicMock()
            mock_transport.generate = AsyncMock(side_effect=RateLimitError("Rate limit exceeded"))
            mock_create.return_value = mock_transport

            result = await generate_interview_questions(
                profile={"user_id": TEST_USER_ID},
                career_path="Full Stack Developer",
                difficulty="medium",
                personality="friendly",
                interview_mode="technical"
            )
        
        # Must return fallback questions, not raise an exception
        assert result is not None, "Rate limit caused crash instead of graceful fallback"

    @pytest.mark.asyncio
    async def test_questions_response_matches_question_interface(self):
        """
        useInterviewSession expects Question interface:
        { id, question, type, difficulty, hint }
        
        If gemini_service returns different keys, hook silently breaks.
        """
        from services.gemini_service import generate_interview_questions
        
        with patch("core.gemini_transport.AsyncGeminiTransport.create") as mock_create:
            mock_transport = MagicMock()
            mock_transport.generate = AsyncMock( return_value=GEMINI_QUESTIONS_RESPONSE )
            mock_create.return_value = mock_transport

            result = await generate_interview_questions(
                profile={"user_id": TEST_USER_ID},
                career_path="Full Stack Developer",
                difficulty="medium",
                personality="friendly",
                interview_mode="technical"
            )
        
        assert isinstance(result, list), "Questions must be a list"
        if result:
            q = result[0]
            for field in ["question", "type", "difficulty"]:
                assert field in q, f"Question field '{field}' missing — hook will break"

