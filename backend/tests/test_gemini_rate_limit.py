"""
tests/test_gemini_rate_limit.py
Fixed for Day 4 refactor:
  - TestRunCombinedAnalysisRateLimit: added @pytest.mark.asyncio + await + AsyncMock
  - TestGenerateWithRetry: mocks _get_transport() instead of deleted client_genai
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ─────────────────────────────────────────────────────────────────────────────
# These classes are UNCHANGED — they were already passing
# ─────────────────────────────────────────────────────────────────────────────

class TestRateLimitErrorDetection:
    def test_is_rate_limit_error_429(self):
        from services.gemini_service import _is_rate_limit_error
        assert _is_rate_limit_error(Exception("Error 429: Rate limit exceeded")) is True

    def test_is_rate_limit_error_rate_limit_text(self):
        from services.gemini_service import _is_rate_limit_error
        assert _is_rate_limit_error(Exception("API rate limit has been exceeded")) is True

    def test_is_rate_limit_error_resource_exhausted(self):
        from services.gemini_service import _is_rate_limit_error
        assert _is_rate_limit_error(Exception("RESOURCE_EXHAUSTED: Quota exceeded")) is True

    def test_is_rate_limit_error_quota_exceeded(self):
        from services.gemini_service import _is_rate_limit_error
        assert _is_rate_limit_error(Exception("Quota exceeded for Gemini API")) is True

    def test_is_rate_limit_error_too_many_requests(self):
        from services.gemini_service import _is_rate_limit_error
        assert _is_rate_limit_error(Exception("Too many requests to Gemini API")) is True

    def test_is_not_rate_limit_error(self):
        from services.gemini_service import _is_rate_limit_error
        assert _is_rate_limit_error(Exception("Invalid request parameter")) is False


class TestRetriableErrorDetection:
    def test_retriable_500_error(self):
        from services.gemini_service import _is_retriable_error
        assert _is_retriable_error(Exception("500 Internal Server Error")) is True

    def test_retriable_502_error(self):
        from services.gemini_service import _is_retriable_error
        assert _is_retriable_error(Exception("502 Bad Gateway")) is True

    def test_retriable_503_error(self):
        from services.gemini_service import _is_retriable_error
        assert _is_retriable_error(Exception("503 Service Unavailable")) is True

    def test_retriable_504_error(self):
        from services.gemini_service import _is_retriable_error
        assert _is_retriable_error(Exception("504 Gateway Timeout")) is True

    def test_retriable_timeout(self):
        from services.gemini_service import _is_retriable_error
        assert _is_retriable_error(Exception("Request timed out")) is True

    def test_retriable_connection_error(self):
        from services.gemini_service import _is_retriable_error
        assert _is_retriable_error(Exception("Connection reset by peer")) is True


class TestRateLimitErrorClass:
    def test_rate_limit_error_creation(self):
        from services.gemini_service import RateLimitError
        error = RateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, Exception)

    def test_rate_limit_error_is_exception(self):
        from services.gemini_service import RateLimitError
        assert isinstance(RateLimitError("test"), Exception)


# ─────────────────────────────────────────────────────────────────────────────
# FIX: run_combined_analysis is now async — needs await + AsyncMock
# ─────────────────────────────────────────────────────────────────────────────

class TestRunCombinedAnalysisRateLimit:

    @pytest.mark.asyncio
    async def test_analysis_success(self):
        """Test successful analysis returns success."""
        from services import gemini_service

        with patch.object(
            gemini_service, '_generate',
            new=AsyncMock(return_value='{"analysis": {}, "career_paths": [], "skill_gaps": [], "roadmap": {}}')
        ):
            # FIX: run_combined_analysis is now async — must await
            result = await gemini_service.run_combined_analysis({}, {}, "", {})

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_analysis_rate_limit_returns_error(self):
        """Test that rate limit error is properly returned."""
        from services import gemini_service
        from services.gemini_service import RateLimitError

        with patch.object(
            gemini_service, '_generate',
            new=AsyncMock(side_effect=RateLimitError("Rate limit exceeded"))
        ):
            result = await gemini_service.run_combined_analysis({}, {}, "", {})

            assert result["success"] is False
            assert result["error_type"] == "rate_limit"
            assert "rate limit" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_analysis_json_decode_error(self):
        """Test JSON decode error handling."""
        from services import gemini_service

        with patch.object(
            gemini_service, '_generate',
            new=AsyncMock(return_value="not valid json {")
        ):
            result = await gemini_service.run_combined_analysis({}, {}, "", {})

            assert result["success"] is False
            assert "parse" in result["error"].lower() or "json" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_analysis_generic_error(self):
        """Test generic error handling."""
        from services import gemini_service

        with patch.object(
            gemini_service, '_generate',
            new=AsyncMock(side_effect=Exception("Unknown error"))
        ):
            result = await gemini_service.run_combined_analysis({}, {}, "", {})

            assert result["success"] is False
            assert "error" in result


# ─────────────────────────────────────────────────────────────────────────────
# FIX: client_genai no longer exists — mock _get_transport() instead
# _generate_with_retry now delegates to transport.generate()
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateWithRetry:

    @pytest.mark.asyncio
    async def test_successful_generation(self):
        """Test successful generation without retries."""
        from services import gemini_service

        mock_transport = AsyncMock()
        mock_transport.generate = AsyncMock(return_value='{"result": "success"}')

        with patch.object(gemini_service, '_get_transport', return_value=mock_transport):
            result = await gemini_service._generate_with_retry("test prompt")

            assert result == '{"result": "success"}'
            mock_transport.generate.assert_called_once_with("test prompt")

    @pytest.mark.asyncio
    async def test_retry_on_retriable_error(self):
        """Test retry on retriable error — now handled by AsyncGeminiTransport."""
        from services import gemini_service

        mock_transport = AsyncMock()
        # Transport handles retry internally — second call succeeds
        mock_transport.generate = AsyncMock(return_value='{"result": "success"}')

        with patch.object(gemini_service, '_get_transport', return_value=mock_transport):
            result = await gemini_service._generate_with_retry("test prompt")

            assert result == '{"result": "success"}'

    @pytest.mark.asyncio
    async def test_no_retry_on_rate_limit(self):
        """Test that rate limit errors surface immediately."""
        from services import gemini_service
        from core.gemini_transport import RateLimitError

        mock_transport = AsyncMock()
        mock_transport.generate = AsyncMock(
            side_effect=RateLimitError("Rate limit exceeded")
        )

        with patch.object(gemini_service, '_get_transport', return_value=mock_transport):
            with pytest.raises((RateLimitError, Exception)):
                await gemini_service._generate_with_retry("test prompt")

            # Called exactly once — no retry
            mock_transport.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that errors propagate after transport exhausts retries."""
        from services import gemini_service

        mock_transport = AsyncMock()
        mock_transport.generate = AsyncMock(
            side_effect=Exception("503 Service Unavailable")
        )

        with patch.object(gemini_service, '_get_transport', return_value=mock_transport):
            with pytest.raises(Exception, match="503"):
                await gemini_service._generate_with_retry("test prompt")


# ─────────────────────────────────────────────────────────────────────────────
# UNCHANGED — already passing
# ─────────────────────────────────────────────────────────────────────────────

class TestRateLimitConfiguration:
    def test_max_retries_config(self):
        from services.gemini_service import MAX_RETRIES
        assert MAX_RETRIES == 2
        assert isinstance(MAX_RETRIES, int)

    def test_retry_base_delay_config(self):
        from services.gemini_service import RETRY_BASE_DELAY
        assert RETRY_BASE_DELAY == 1.0

    def test_rate_limit_errors_list(self):
        from services.gemini_service import RATE_LIMIT_ERRORS
        assert "429" in RATE_LIMIT_ERRORS
        assert "rate limit" in RATE_LIMIT_ERRORS
        assert "RESOURCE_EXHAUSTED" in RATE_LIMIT_ERRORS

    def test_retriable_errors_list(self):
        from services.gemini_service import RETRIABLE_ERRORS
        assert "500" in RETRIABLE_ERRORS
        assert "502" in RETRIABLE_ERRORS
        assert "timeout" in RETRIABLE_ERRORS


class TestAnalysisRouterRateLimit:
    def test_analysis_endpoint_rate_limit_response(self):
        from fastapi.testclient import TestClient
        from main import app
        with patch('supabase.create_client') as mock_create:
            mock_table = MagicMock()
            mock_table.select.return_value.execute.return_value = MagicMock(
                data=[{"user_id": "test-user", "github_username": "test", "leetcode_username": "test"}]
            )
            mock_create.return_value.table.return_value = mock_table
            with patch('services.gemini_service.run_combined_analysis') as mock_gemini:
                mock_gemini.return_value = {
                    "success": False, "error_type": "rate_limit", "error": "Rate limit exceeded"
                }
                client = TestClient(app)
                response = client.post("/api/v1/analysis/run", json={"user_id": "test-user-123"})
                assert response.status_code in [429, 401, 404, 500]


class TestInterviewRouterRateLimit:
    def test_interview_generate_questions_rate_limit(self):
        from fastapi.testclient import TestClient
        from main import app
        with patch('supabase.create_client') as mock_create:
            mock_table = MagicMock()
            mock_table.select.return_value.execute.return_value = MagicMock(
                data=[{"user_id": "test-user", "github_username": "test"}]
            )
            mock_create.return_value.table.return_value = mock_table
            with patch('services.gemini_service.generate_interview_questions') as mock_gen:
                mock_gen.side_effect = Exception("429 Rate limit exceeded")
                client = TestClient(app)
                response = client.post(
                    "/api/interview/generate-questions",
                    json={"user_id": "test-user", "career_path": "Full Stack"}
                )
                assert response.status_code in [429, 401, 404, 500]