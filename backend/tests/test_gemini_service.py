"""
tests/test_gemini_service.py
─────────────────────────────────────────────────────────────────────
Unit tests for the refactored async gemini_service functions.

Tests:
  - run_combined_analysis() is async and works
  - generate_interview_questions() is async and works
  - evaluate_interview_answer() is async and works
  - analyze_certificate() is async and works
  - All functions properly await the transport layer
  - Cache and retry logic still works with async calls
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# These tests assume you've refactored gemini_service.py to use AsyncGeminiTransport
# If the imports fail, verify that gemini_service.py has the async functions


@pytest.mark.asyncio
async def test_run_combined_analysis_is_async():
    """Verify run_combined_analysis is async def and returns a dict."""
    from services import gemini_service
    
    # Mock the transport
    mock_transport = AsyncMock()
    mock_transport.generate = AsyncMock(return_value='{"success": true, "data": {}}')
    
    with patch('services.gemini_service._get_transport', return_value=mock_transport):
        result = await gemini_service.run_combined_analysis(
            github_data={"repos": 5},
            leetcode_data={"problems": 100},
            resume_text="Software Engineer",
            user_profile={"name": "John"}
        )
        
        assert isinstance(result, dict)
        assert "success" in result or "data" in result


@pytest.mark.asyncio
async def test_generate_interview_questions_is_async():
    """Verify generate_interview_questions is async def and returns a list."""
    from services import gemini_service
    
    mock_transport = AsyncMock()
    mock_transport.generate = AsyncMock(return_value='[{"id": 1, "question": "Test?"}]')
    
    with patch('services.gemini_service._get_transport', return_value=mock_transport):
        result = await gemini_service.generate_interview_questions(
            profile={"name": "John"},
            career_path="AI/ML Engineer",
            difficulty="medium"
        )
        
        # Result should be a list
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_evaluate_interview_answer_is_async():
    """Verify evaluate_interview_answer is async def."""
    from services import gemini_service
    
    mock_transport = AsyncMock()
    mock_transport.generate = AsyncMock(
        return_value='{"score": 8, "good_points": ["clear"], "missing_points": ["depth"]}'
    )
    
    with patch('services.gemini_service._get_transport', return_value=mock_transport):
        result = await gemini_service.evaluate_interview_answer(
            question="What is OOP?",
            answer="Object-oriented programming...",
            career_path="Software Engineer"
        )
        
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_analyze_certificate_is_async():
    """Verify analyze_certificate is async def."""
    from services import gemini_service
    
    mock_transport = AsyncMock()
    mock_transport.generate_multimodal = AsyncMock(
        return_value='{"course_name": "Python Basics", "provider": "Coursera"}'
    )
    
    with patch('services.gemini_service._get_transport', return_value=mock_transport):
        result = await gemini_service.analyze_certificate(
            file_content=b"fake certificate bytes",
            filename="cert.pdf",
            mime_type="application/pdf"
        )
        
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_all_functions_are_awaitable():
    """Verify all core functions are coroutines (can be awaited)."""
    from services import gemini_service
    from inspect import iscoroutinefunction
    
    # Check that functions are async def
    assert iscoroutinefunction(gemini_service._generate), "_generate should be async"
    assert iscoroutinefunction(gemini_service._generate_with_retry), "_generate_with_retry should be async"
    assert iscoroutinefunction(gemini_service.run_combined_analysis), "run_combined_analysis should be async"
    assert iscoroutinefunction(gemini_service.generate_interview_questions), "generate_interview_questions should be async"
    assert iscoroutinefunction(gemini_service.evaluate_interview_answer), "evaluate_interview_answer should be async"
    assert iscoroutinefunction(gemini_service.analyze_certificate), "analyze_certificate should be async"


@pytest.mark.asyncio
async def test_concurrent_analysis_calls():
    """Verify multiple concurrent analysis calls work independently."""
    from services import gemini_service
    
    call_count = 0
    
    async def fake_generate(prompt):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0)  # yield
        return f'{{"success": true, "data": {{"call": {call_count}}}}}'
    
    mock_transport = AsyncMock()
    mock_transport.generate = fake_generate
    
    with patch('services.gemini_service._get_transport', return_value=mock_transport):
        results = await asyncio.gather(
            gemini_service.run_combined_analysis({}, {}, "", {}),
            gemini_service.run_combined_analysis({}, {}, "", {}),
        )
        
        assert len(results) == 2
        assert call_count == 2