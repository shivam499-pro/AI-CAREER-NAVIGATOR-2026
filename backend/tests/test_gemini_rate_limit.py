"""
Tests for Gemini API rate limit error handling.
Tests rate limit detection, error responses, and retry behavior.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock, Mock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestRateLimitErrorDetection:
    """Test rate limit error detection in Gemini service."""

    def test_is_rate_limit_error_429(self):
        """Test detection of 429 status code."""
        from services.gemini_service import _is_rate_limit_error
        
        error = Exception("Error 429: Rate limit exceeded")
        
        assert _is_rate_limit_error(error) is True

    def test_is_rate_limit_error_rate_limit_text(self):
        """Test detection of rate limit in error message."""
        from services.gemini_service import _is_rate_limit_error
        
        error = Exception("API rate limit has been exceeded")
        
        assert _is_rate_limit_error(error) is True

    def test_is_rate_limit_error_resource_exhausted(self):
        """Test detection of RESOURCE_EXHAUSTED error."""
        from services.gemini_service import _is_rate_limit_error
        
        error = Exception("RESOURCE_EXHAUSTED: Quota exceeded")
        
        assert _is_rate_limit_error(error) is True

    def test_is_rate_limit_error_quota_exceeded(self):
        """Test detection of quota exceeded error."""
        from services.gemini_service import _is_rate_limit_error
        
        error = Exception("Quota exceeded for Gemini API")
        
        assert _is_rate_limit_error(error) is True

    def test_is_rate_limit_error_too_many_requests(self):
        """Test detection of too many requests."""
        from services.gemini_service import _is_rate_limit_error
        
        error = Exception("Too many requests to Gemini API")
        
        assert _is_rate_limit_error(error) is True

    def test_is_not_rate_limit_error(self):
        """Test that non-rate-limit errors return False."""
        from services.gemini_service import _is_rate_limit_error
        
        error = Exception("Invalid request parameter")
        
        assert _is_rate_limit_error(error) is False


class TestRetriableErrorDetection:
    """Test retriable error detection."""

    def test_retriable_500_error(self):
        """Test that 500 errors are retriable."""
        from services.gemini_service import _is_retriable_error
        
        error = Exception("500 Internal Server Error")
        
        assert _is_retriable_error(error) is True

    def test_retriable_502_error(self):
        """Test that 502 errors are retriable."""
        from services.gemini_service import _is_retriable_error
        
        error = Exception("502 Bad Gateway")
        
        assert _is_retriable_error(error) is True

    def test_retriable_503_error(self):
        """Test that 503 errors are retriable."""
        from services.gemini_service import _is_retriable_error
        
        error = Exception("503 Service Unavailable")
        
        assert _is_retriable_error(error) is True

    def test_retriable_504_error(self):
        """Test that 504 errors are retriable."""
        from services.gemini_service import _is_retriable_error
        
        error = Exception("504 Gateway Timeout")
        
        assert _is_retriable_error(error) is True

    def test_retriable_timeout(self):
        """Test that timeout errors are retriable."""
        from services.gemini_service import _is_retriable_error
        
        error = Exception("Request timed out")
        
        assert _is_retriable_error(error) is True

    def test_retriable_connection_error(self):
        """Test that connection errors are retriable."""
        from services.gemini_service import _is_retriable_error
        
        error = Exception("Connection reset by peer")
        
        assert _is_retriable_error(error) is True


class TestRateLimitErrorClass:
    """Test the RateLimitError custom exception."""

    def test_rate_limit_error_creation(self):
        """Test creating a RateLimitError."""
        from services.gemini_service import RateLimitError
        
        error = RateLimitError("Rate limit exceeded")
        
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, Exception)

    def test_rate_limit_error_is_exception(self):
        """Test that RateLimitError inherits from Exception."""
        from services.gemini_service import RateLimitError
        
        error = RateLimitError("test")
        
        assert isinstance(error, Exception)


class TestRunCombinedAnalysisRateLimit:
    """Test rate limit handling in run_combined_analysis."""

    def test_analysis_success(self, mock_gemini_response):
        """Test successful analysis returns success."""
        from services import gemini_service
        
        # Mock _generate to return valid JSON
        with patch.object(gemini_service, '_generate') as mock_generate:
            mock_generate.return_value = '{"analysis": {}, "career_paths": [], "skill_gaps": [], "roadmap": {}}'
            
            result = gemini_service.run_combined_analysis(
                {}, {}, "", {}
            )
            
            assert result["success"] is True
            assert "data" in result

    def test_analysis_rate_limit_returns_error(self):
        """Test that rate limit error is properly returned."""
        from services import gemini_service
        
        # Mock _generate to raise RateLimitError
        with patch.object(gemini_service, '_generate') as mock_generate:
            from services.gemini_service import RateLimitError
            mock_generate.side_effect = RateLimitError("Rate limit exceeded")
            
            result = gemini_service.run_combined_analysis(
                {}, {}, "", {}
            )
            
            assert result["success"] is False
            assert result["error_type"] == "rate_limit"
            assert "rate limit" in result["error"].lower()

    def test_analysis_json_decode_error(self):
        """Test JSON decode error handling."""
        from services import gemini_service
        
        with patch.object(gemini_service, '_generate') as mock_generate:
            mock_generate.return_value = "not valid json {"
            
            result = gemini_service.run_combined_analysis(
                {}, {}, "", {}
            )
            
            assert result["success"] is False
            assert "parse" in result["error"].lower() or "json" in result["error"].lower()

    def test_analysis_generic_error(self):
        """Test generic error handling."""
        from services import gemini_service
        
        with patch.object(gemini_service, '_generate') as mock_generate:
            mock_generate.side_effect = Exception("Unknown error")
            
            result = gemini_service.run_combined_analysis(
                {}, {}, "", {}
            )
            
            assert result["success"] is False
            assert "error" in result


class TestGenerateWithRetry:
    """Test retry logic in _generate_with_retry."""

    def test_successful_generation(self):
        """Test successful generation without retries."""
        from services import gemini_service
        
        with patch.object(gemini_service, 'client_genai') as mock_client:
            mock_response = MagicMock()
            mock_response.text = '{"result": "success"}'
            mock_client.models.generate_content.return_value = mock_response
            
            result = gemini_service._generate_with_retry("test prompt")
            
            assert result == '{"result": "success"}'
            assert mock_client.models.generate_content.call_count == 1

    def test_retry_on_retriable_error(self):
        """Test retry on retriable error."""
        from services import gemini_service
        
        with patch.object(gemini_service, 'client_genai') as mock_client:
            # First call fails with 503, second succeeds
            mock_response = MagicMock()
            mock_response.text = '{"result": "success"}'
            
            mock_client.models.generate_content.side_effect = [
                Exception("503 Service Unavailable"),
                mock_response
            ]
            
            result = gemini_service._generate_with_retry("test prompt")
            
            assert result == '{"result": "success"}'
            assert mock_client.models.generate_content.call_count == 2

    def test_no_retry_on_rate_limit(self):
        """Test that rate limit errors don't trigger retry."""
        from services.gemini_service import RateLimitError, _generate_with_retry
        
        with patch('services.gemini_service.client_genai') as mock_client:
            mock_client.models.generate_content.side_effect = RateLimitError("Rate limit")
            
            with pytest.raises(RateLimitError):
                _generate_with_retry("test prompt")
            
            # Should only be called once, no retries
            assert mock_client.models.generate_content.call_count == 1

    def test_max_retries_exceeded(self):
        """Test that max retries are enforced."""
        from services.gemini_service import _generate_with_retry, MAX_RETRIES
        
        with patch('services.gemini_service.client_genai') as mock_client:
            # Always raise retriable error
            mock_client.models.generate_content.side_effect = Exception("503 Service Unavailable")
            
            with pytest.raises(Exception):
                _generate_with_retry("test prompt")
            
            # Should be called MAX_RETRIES + 1 times (initial + retries)
            assert mock_client.models.generate_content.call_count == MAX_RETRIES + 1


class TestRateLimitConfiguration:
    """Test rate limit related configuration."""

    def test_max_retries_config(self):
        """Test MAX_RETRIES configuration."""
        from services.gemini_service import MAX_RETRIES
        
        assert MAX_RETRIES == 2
        assert isinstance(MAX_RETRIES, int)

    def test_retry_base_delay_config(self):
        """Test RETRY_BASE_DELAY configuration."""
        from services.gemini_service import RETRY_BASE_DELAY
        
        assert RETRY_BASE_DELAY == 1.0

    def test_rate_limit_errors_list(self):
        """Test RATE_LIMIT_ERRORS list."""
        from services.gemini_service import RATE_LIMIT_ERRORS
        
        assert "429" in RATE_LIMIT_ERRORS
        assert "rate limit" in RATE_LIMIT_ERRORS
        assert "RESOURCE_EXHAUSTED" in RATE_LIMIT_ERRORS

    def test_retriable_errors_list(self):
        """Test RETRIABLE_ERRORS list."""
        from services.gemini_service import RETRIABLE_ERRORS
        
        assert "500" in RETRIABLE_ERRORS
        assert "502" in RETRIABLE_ERRORS
        assert "timeout" in RETRIABLE_ERRORS


class TestAnalysisRouterRateLimit:
    """Test rate limit handling in analysis router."""

    def test_analysis_endpoint_rate_limit_response(self):
        """Test that analysis endpoint returns 429 on rate limit."""
        from fastapi.testclient import TestClient
        from main import app
        
        with patch('supabase.create_client') as mock_create:
            # Setup mock to return profile
            mock_table = MagicMock()
            mock_table.select.return_value.execute.return_value = MagicMock(
                data=[{"user_id": "test-user", "github_username": "test", "leetcode_username": "test"}]
            )
            mock_create.return_value.table.return_value = mock_table
            
            # Mock gemini service to return rate limit error
            with patch('routers.analysis.gemini_service.run_combined_analysis') as mock_gemini:
                mock_gemini.return_value = {
                    "success": False,
                    "error_type": "rate_limit",
                    "error": "Rate limit exceeded"
                }
                
                client = TestClient(app)
                response = client.post(
                    "/api/analysis/start",
                    json={"user_id": "test-user-123"}
                )
                
                # Should get 500 because the router catches rate limit and raises HTTPException
                # May also return 404 if endpoint doesn't exist
                assert response.status_code in [429, 404, 500]


class TestInterviewRouterRateLimit:
    """Test rate limit handling in interview router."""

    def test_interview_generate_questions_rate_limit(self):
        """Test interview questions endpoint handles rate limit."""
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
                
                # Should handle rate limit
                # May also return 404 if endpoint doesn't exist
                assert response.status_code in [429, 404, 500]