from unittest.mock import patch

from utils import (
    create_response,
    with_timing,
    logStructured,
    safe_timeout,
    handle_service_error,
)


# ------------------------------------------------------------------
# create_response
# ------------------------------------------------------------------

def test_create_response_defaults():
    response = create_response()

    assert response["success"] is True
    assert response["data"] is None
    assert response["error"] is None
    assert response["source"] == "db"

    assert "meta" in response
    assert "timestamp" in response["meta"]
    assert response["meta"]["execution_time_ms"] == 0


def test_create_response_custom_values():
    response = create_response(
        data={"name": "test"},
        success=False,
        error="something failed",
        source="cache",
    )

    assert response["success"] is False
    assert response["data"] == {"name": "test"}
    assert response["error"] == "something failed"
    assert response["source"] == "cache"


# ------------------------------------------------------------------
# with_timing
# ------------------------------------------------------------------

def test_with_timing_updates_execution_time():
    @with_timing
    def sample():
        return {
            "meta": {
                "execution_time_ms": 0
            }
        }

    result = sample()

    assert "meta" in result
    assert "execution_time_ms" in result["meta"]
    assert isinstance(result["meta"]["execution_time_ms"], int)
    assert result["meta"]["execution_time_ms"] >= 0


def test_with_timing_dict_without_meta():
    @with_timing
    def sample():
        return {"message": "ok"}

    result = sample()

    assert result == {"message": "ok"}


def test_with_timing_non_dict():
    @with_timing
    def sample():
        return "success"

    result = sample()

    assert result == "success"


# ------------------------------------------------------------------
# logStructured
# ------------------------------------------------------------------

@patch("utils.logger")
def test_log_structured_success(mock_logger):
    logStructured(
        module="TEST",
        action="run",
        user_id="123",
        status="success",
        latency_ms=25,
    )

    mock_logger.info.assert_called_once()

    logged_message = mock_logger.info.call_args[0][0]

    assert "[BACKEND][TEST]" in logged_message
    assert "action=run" in logged_message
    assert "user_id=123" in logged_message
    assert "status=success" in logged_message
    assert "latency_ms=25" in logged_message


@patch("utils.logger")
def test_log_structured_error(mock_logger):
    logStructured(
        module="TEST",
        action="run",
        status="error",
        latency_ms=10,
    )

    mock_logger.error.assert_called_once()

    logged_message = mock_logger.error.call_args[0][0]

    assert "[BACKEND][TEST]" in logged_message
    assert "status=error" in logged_message
    assert "latency_ms=10" in logged_message


# ------------------------------------------------------------------
# safe_timeout
# ------------------------------------------------------------------

def test_safe_timeout_default():
    @safe_timeout()
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_safe_timeout_custom_seconds():
    @safe_timeout(10)
    def multiply(a, b):
        return a * b

    assert multiply(4, 5) == 20


# ------------------------------------------------------------------
# handle_service_error
# ------------------------------------------------------------------

@patch("utils.logger")
def test_handle_service_error(mock_logger):
    result = handle_service_error(
        module="INTERVIEW",
        action="generate_questions",
        fallback_data={"questions": []},
        user_id="user123",
    )

    mock_logger.error.assert_called_once()

    assert result["success"] is False
    assert result["data"] == {"questions": []}
    assert result["error"] == "Service temporarily unavailable"
    assert result["source"] == "error_handler"

    assert "meta" in result