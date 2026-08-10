"""
Additional tests for services/interview_service.py filling in coverage gaps
left by tests/test_interview_service.py:

- generate_questions: throttled with no cache -> fallback branch
- generate_questions: rate-limit retry that succeeds, and retry that fails
- generate_questions: AI returns an empty/invalid list -> "fallback" source
  (as opposed to the "exception_fallback" path already covered)
- evaluate_answer: exception branch
- get_hint: exception branch
- _set_cached_questions: LRU eviction once max_cached_question_sets is exceeded
- _call_gemini_for_questions: returns None when gemini_service returns a
  non-list or empty list
"""
import pytest
from unittest.mock import AsyncMock, patch

from services.interview_service import InterviewService, InterviewServiceConfig
from core.gemini_transport import AsyncGeminiTransport


@pytest.fixture
def mock_transport():
    transport = AsyncMock(spec=AsyncGeminiTransport)
    return transport


FAKE_QUESTIONS = [
    {"id": 1, "question": "What is OOP?", "type": "technical"},
    {"id": 2, "question": "Describe a project.", "type": "behavioral"},
    {"id": 3, "question": "What are your strengths?", "type": "behavioral"},
]


# ─── generate_questions: throttled with no cache -> fallback ───────────────

@pytest.mark.asyncio
async def test_generate_questions_throttled_with_no_cache_returns_fallback(mock_transport):
    config = InterviewServiceConfig(
        questions_cache_ttl_seconds=5, user_throttle_seconds=100, max_cached_question_sets=3
    )
    service = InterviewService(transport=mock_transport, config=config)

    # First call establishes the throttle timestamp for this user.
    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(return_value=FAKE_QUESTIONS),
    ):
        await service.generate_questions(user_id="throttle_user", career_path="Backend")

    # Second call (different career_path so nothing is cached for it) hits
    # the throttle branch with no cached questions -> fallback.
    result = await service.generate_questions(user_id="throttle_user", career_path="Frontend")

    assert result["success"] is True
    assert result["source"] == "throttle_fallback"
    assert result["meta"]["cached"] is False
    assert len(result["questions"]) == 10


# ─── generate_questions: rate-limit retry ──────────────────────────────────

@pytest.mark.asyncio
async def test_generate_questions_retries_once_on_rate_limit_and_succeeds(mock_transport):
    config = InterviewServiceConfig(
        questions_cache_ttl_seconds=5, user_throttle_seconds=0, max_cached_question_sets=3
    )
    service = InterviewService(transport=mock_transport, config=config)

    call_count = {"n": 0}

    async def flaky(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("Rate limit exceeded (429)")
        return FAKE_QUESTIONS

    with patch(
        "services.gemini_service.generate_interview_questions", new=AsyncMock(side_effect=flaky)
    ), patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        result = await service.generate_questions(user_id="retry_user", career_path="Backend")

    assert result["success"] is True
    assert result["source"] == "ai"
    assert result["meta"]["retry_used"] is True
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_generate_questions_retry_also_fails_falls_back_to_fallback_questions(mock_transport):
    config = InterviewServiceConfig(
        questions_cache_ttl_seconds=5, user_throttle_seconds=0, max_cached_question_sets=3
    )
    service = InterviewService(transport=mock_transport, config=config)

    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(side_effect=Exception("429 rate limit")),
    ), patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        result = await service.generate_questions(user_id="retry_fail_user", career_path="Backend")

    assert result["success"] is True
    assert result["source"] == "fallback"
    assert result["meta"]["retry_used"] is True
    assert len(result["questions"]) == 10


@pytest.mark.asyncio
async def test_generate_questions_non_rate_limit_error_propagates_to_outer_handler(mock_transport):
    """A non-rate-limit AI error should re-raise out of the inner except and
    be caught by the outer handler, yielding 'exception_fallback'."""
    config = InterviewServiceConfig(
        questions_cache_ttl_seconds=5, user_throttle_seconds=0, max_cached_question_sets=3
    )
    service = InterviewService(transport=mock_transport, config=config)

    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(side_effect=ValueError("some other failure")),
    ):
        result = await service.generate_questions(user_id="other_error_user", career_path="Backend")

    assert result["success"] is True
    assert result["source"] == "exception_fallback"


# ─── generate_questions: AI returns empty list -> non-exception fallback ───

@pytest.mark.asyncio
async def test_generate_questions_empty_ai_result_uses_fallback_source(mock_transport):
    config = InterviewServiceConfig(
        questions_cache_ttl_seconds=5, user_throttle_seconds=0, max_cached_question_sets=3
    )
    service = InterviewService(transport=mock_transport, config=config)

    with patch(
        "services.gemini_service.generate_interview_questions", new=AsyncMock(return_value=[])
    ):
        result = await service.generate_questions(user_id="empty_user", career_path="Backend")

    assert result["success"] is True
    assert result["source"] == "fallback"
    assert result["meta"]["retry_used"] is False
    assert len(result["questions"]) == 10


# ─── _call_gemini_for_questions: invalid / non-list return ─────────────────

@pytest.mark.asyncio
async def test_call_gemini_for_questions_returns_none_for_non_list_result(mock_transport):
    config = InterviewServiceConfig(
        questions_cache_ttl_seconds=5, user_throttle_seconds=0, max_cached_question_sets=3
    )
    service = InterviewService(transport=mock_transport, config=config)

    with patch(
        "services.gemini_service.generate_interview_questions",
        new=AsyncMock(return_value={"not": "a list"}),
    ):
        result = await service._call_gemini_for_questions(
            {}, "Backend", "medium", "", "friendly", "technical"
        )

    assert result is None


# ─── evaluate_answer: exception branch ─────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_answer_returns_error_dict_on_exception(mock_transport):
    service = InterviewService(transport=mock_transport)

    with patch(
        "services.gemini_service.evaluate_interview_answer",
        new=AsyncMock(side_effect=Exception("gemini down")),
    ):
        result = await service.evaluate_answer("What is OOP?", "My answer", "Backend")

    assert result["success"] is False
    assert result["error"] == "evaluation_failed"
    assert "try again" in result["message"].lower()


@pytest.mark.asyncio
async def test_evaluate_answer_returns_gemini_result_on_success(mock_transport):
    service = InterviewService(transport=mock_transport)

    with patch(
        "services.gemini_service.evaluate_interview_answer",
        new=AsyncMock(return_value={"success": True, "score": 8}),
    ):
        result = await service.evaluate_answer("What is OOP?", "My answer", "Backend")

    assert result == {"success": True, "score": 8}


# ─── get_hint: exception branch ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_hint_returns_default_hint_on_transport_error(mock_transport):
    mock_transport.generate = AsyncMock(side_effect=Exception("transport down"))
    service = InterviewService(transport=mock_transport)

    result = await service.get_hint("What is OOP?", "Backend")

    assert "looking_for" in result
    assert "structure" in result
    assert "example" in result
    assert "STAR" in result["structure"]


@pytest.mark.asyncio
async def test_get_hint_returns_default_hint_on_malformed_json(mock_transport):
    mock_transport.generate = AsyncMock(return_value="not valid json {{{")
    service = InterviewService(transport=mock_transport)

    result = await service.get_hint("What is OOP?", "Backend")

    assert result["looking_for"] == "Focus on demonstrating your skills and experience."


@pytest.mark.asyncio
async def test_get_hint_parses_valid_json_response(mock_transport):
    mock_transport.generate = AsyncMock(
        return_value='{"looking_for": "clarity", "structure": "STAR", "example": "example"}'
    )
    service = InterviewService(transport=mock_transport)

    result = await service.get_hint("What is OOP?", "Backend")

    assert result == {"looking_for": "clarity", "structure": "STAR", "example": "example"}


# ─── _set_cached_questions: LRU eviction ───────────────────────────────────

@pytest.mark.asyncio
async def test_cache_evicts_oldest_entry_once_max_size_exceeded(mock_transport):
    config = InterviewServiceConfig(
        questions_cache_ttl_seconds=999, user_throttle_seconds=0, max_cached_question_sets=2
    )
    service = InterviewService(transport=mock_transport, config=config)

    with patch(
        "services.gemini_service.generate_interview_questions", new=AsyncMock(return_value=FAKE_QUESTIONS)
    ):
        await service.generate_questions(user_id="user_a", career_path="Backend")
        await service.generate_questions(user_id="user_b", career_path="Backend")
        # Third distinct cache entry should evict the oldest (user_a's).
        await service.generate_questions(user_id="user_c", career_path="Backend")

    assert len(service._questions_cache) == 2
    assert service._get_cache_key("user_a", "Backend", "medium") not in service._questions_cache
    assert service._get_cache_key("user_b", "Backend", "medium") in service._questions_cache
    assert service._get_cache_key("user_c", "Backend", "medium") in service._questions_cache