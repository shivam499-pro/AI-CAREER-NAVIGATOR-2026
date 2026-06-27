"""
tests/test_interview_service.py
Tests for InterviewService
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from services.interview_service import InterviewService, InterviewServiceConfig
from core.gemini_transport import AsyncGeminiTransport


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_transport():
    transport = AsyncMock(spec=AsyncGeminiTransport)
    transport.generate = AsyncMock(
        return_value='{"looking_for": "skills", "structure": "STAR", "example": "example text"}'
    )
    return transport


@pytest.fixture
def service(mock_transport):
    """Standard service — throttle=2s for throttle-specific tests."""
    config = InterviewServiceConfig(
        questions_cache_ttl_seconds=5,
        user_throttle_seconds=2,
        max_cached_question_sets=3
    )
    return InterviewService(transport=mock_transport, config=config)


@pytest.fixture
def no_throttle_service(mock_transport):
    """Service with throttle disabled — for cache-specific tests."""
    config = InterviewServiceConfig(
        questions_cache_ttl_seconds=5,
        user_throttle_seconds=0,   # ← throttle OFF
        max_cached_question_sets=3
    )
    return InterviewService(transport=mock_transport, config=config)


# Fake questions returned by mocked gemini_service
FAKE_QUESTIONS = [
    {"id": 1, "question": "What is OOP?", "type": "technical"},
    {"id": 2, "question": "Describe a project.", "type": "behavioral"},
    {"id": 3, "question": "What are your strengths?", "type": "behavioral"},
]


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_questions_basic(no_throttle_service):
    """Generate questions from AI."""
    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(return_value=FAKE_QUESTIONS)
    ):
        result = await no_throttle_service.generate_questions(
            user_id="user1",
            career_path="AI/ML Engineer",
            difficulty="medium"
        )

    assert result["success"] is True
    assert len(result["questions"]) > 0
    assert result["source"] == "ai"
    assert result["meta"]["cached"] is False


@pytest.mark.asyncio
async def test_generate_questions_returns_fallback_on_failure(no_throttle_service):
    """Return fallback questions when AI fails.
    
    Note: a generic exception hits the outer except block which returns
    'exception_fallback'. Both 'fallback' and 'exception_fallback' are
    valid fallback responses — we test that questions are returned, not
    the specific label.
    """
    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(side_effect=Exception("API error"))
    ):
        result = await no_throttle_service.generate_questions(
            user_id="user1",
            career_path="AI/ML Engineer"
        )

    assert result["success"] is True
    assert len(result["questions"]) == 10
    # Both are valid fallback paths
    assert result["source"] in ("fallback", "exception_fallback")


@pytest.mark.asyncio
async def test_generate_questions_caches_result(no_throttle_service):
    """Second call with same params returns from cache."""
    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(return_value=FAKE_QUESTIONS)
    ):
        result1 = await no_throttle_service.generate_questions(
            user_id="cache_user", career_path="AI/ML Engineer", difficulty="medium"
        )
        result2 = await no_throttle_service.generate_questions(
            user_id="cache_user", career_path="AI/ML Engineer", difficulty="medium"
        )

    assert result1["source"] == "ai"
    assert result2["source"] == "cache"
    assert result2["meta"]["cached"] is True
    assert result1["questions"] == result2["questions"]


@pytest.mark.asyncio
async def test_generate_questions_different_difficulty_not_cached(no_throttle_service):
    """Different difficulty = separate cache key = separate AI call."""
    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(return_value=FAKE_QUESTIONS)
    ):
        result1 = await no_throttle_service.generate_questions(
            user_id="diff_user", career_path="AI/ML Engineer", difficulty="easy"
        )
        result2 = await no_throttle_service.generate_questions(
            user_id="diff_user", career_path="AI/ML Engineer", difficulty="hard"
        )

    assert result1["source"] == "ai"
    assert result2["source"] == "ai"


@pytest.mark.asyncio
async def test_user_throttled_returns_cache(service):
    """Second request within throttle window returns throttle_cache."""
    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(return_value=FAKE_QUESTIONS)
    ):
        result1 = await service.generate_questions(
            user_id="throttle_user", career_path="Backend Engineer", difficulty="medium"
        )
        result2 = await service.generate_questions(
            user_id="throttle_user", career_path="Backend Engineer", difficulty="medium"
        )

    assert result1["source"] == "ai"
    assert result2["source"] == "throttle_cache"

    # Wait for throttle to expire
    await asyncio.sleep(2.1)

    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(return_value=FAKE_QUESTIONS)
    ):
        result3 = await service.generate_questions(
            user_id="throttle_user", career_path="Backend Engineer", difficulty="medium"
        )

    assert result3["source"] == "cache"


@pytest.mark.asyncio
async def test_cache_expires_after_ttl(no_throttle_service):
    """Cache expires after TTL and AI is called again."""
    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(return_value=FAKE_QUESTIONS)
    ):
        result1 = await no_throttle_service.generate_questions(
            user_id="ttl_user", career_path="Data Engineer"
        )
        assert result1["source"] == "ai"

        result2 = await no_throttle_service.generate_questions(
            user_id="ttl_user", career_path="Data Engineer"
        )
        assert result2["source"] == "cache"

    # Wait for TTL to expire (5s in test config)
    await asyncio.sleep(5.1)

    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(return_value=FAKE_QUESTIONS)
    ):
        result3 = await no_throttle_service.generate_questions(
            user_id="ttl_user", career_path="Data Engineer"
        )

    assert result3["source"] == "ai"


@pytest.mark.asyncio
async def test_evaluate_answer(service):
    """Evaluate answer delegates to gemini_service."""
    with patch(
        "services.gemini_service.evaluate_interview_answer",
        new=AsyncMock(return_value={
            "score": 8,
            "good_points": ["Clear"],
            "missing_points": ["Depth"]
        })
    ):
        result = await service.evaluate_answer(
            question="What is a database?",
            answer="A database is...",
            career_path="Data Engineer"
        )

    assert result["score"] == 8
    assert "Clear" in result["good_points"]


@pytest.mark.asyncio
async def test_get_hint(service, mock_transport):
    """Get hint uses transport directly."""
    mock_transport.generate = AsyncMock(
        return_value='{"looking_for": "design skills", "structure": "STAR", "example": "A project I designed"}'
    )

    result = await service.get_hint(
        question="Design a scalable system",
        career_path="Software Architect"
    )

    assert "looking_for" in result
    assert "structure" in result
    assert "example" in result


@pytest.mark.asyncio
async def test_concurrent_question_generation(no_throttle_service):
    """Multiple concurrent requests for different users work independently."""
    call_count = 0

    async def fake_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0)
        return [{"id": 1, "question": f"Q{call_count}", "type": "technical"}]

    with patch(
        "services.gemini_service.generate_interview_questions",
        new=fake_generate
    ):
        results = await asyncio.gather(
            no_throttle_service.generate_questions("concurrent_user_a", "Career A"),
            no_throttle_service.generate_questions("concurrent_user_b", "Career B"),
        )

    assert len(results) == 2
    assert all(r["success"] is True for r in results)