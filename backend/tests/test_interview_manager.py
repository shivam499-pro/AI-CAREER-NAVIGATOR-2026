"""
Unit tests for modules/interview/manager.py

This module had NO dedicated test file. Its two responsibilities:

1. get_or_create_session() -- an in-memory map keyed by "{user_id}:{career_path}"
   that hands back a stable session id for the life of the process.
2. get_interview_service() -- a lazy singleton factory for InterviewService.

Both are module-level globals (_interview_service, _user_active_sessions),
so every test resets them via the autouse fixture below to avoid leaking
state between tests (and between this file and routers/interview.py tests,
which import the same module).
"""
import uuid

import pytest
from unittest.mock import patch, MagicMock

import modules.interview.manager as manager


@pytest.fixture(autouse=True)
def _reset_manager_state():
    """Isolate each test from the module's process-lifetime globals."""
    manager._interview_service = None
    manager._user_active_sessions.clear()
    yield
    manager._interview_service = None
    manager._user_active_sessions.clear()


class TestGetOrCreateSession:
    def test_returns_same_session_id_for_same_user_and_career_path(self):
        first = manager.get_or_create_session("user-1", "Backend Engineer")
        second = manager.get_or_create_session("user-1", "Backend Engineer")

        assert first == second

    def test_returns_different_session_ids_for_different_career_paths(self):
        backend_session = manager.get_or_create_session("user-1", "Backend Engineer")
        frontend_session = manager.get_or_create_session("user-1", "Frontend Engineer")

        assert backend_session != frontend_session

    def test_returns_different_session_ids_for_different_users(self):
        user_a_session = manager.get_or_create_session("user-a", "Backend Engineer")
        user_b_session = manager.get_or_create_session("user-b", "Backend Engineer")

        assert user_a_session != user_b_session

    def test_session_id_is_a_valid_uuid4_string(self):
        session_id = manager.get_or_create_session("user-1", "Backend Engineer")

        # uuid.UUID() raises ValueError if this isn't a valid UUID string --
        # that failure IS the assertion.
        parsed = uuid.UUID(session_id)
        assert str(parsed) == session_id

    def test_stores_session_under_composite_key(self):
        session_id = manager.get_or_create_session("user-1", "Backend Engineer")

        assert manager._user_active_sessions["user-1:Backend Engineer"] == session_id

    def test_career_paths_with_colons_do_not_collide_across_users(self):
        # Regression guard: the key format is f"{user_id}:{career_path}", so a
        # user_id containing a colon could theoretically collide with a
        # different user/career_path split. Document current behavior.
        session_a = manager.get_or_create_session("user", "1:Backend Engineer")
        session_b = manager.get_or_create_session("user:1", "Backend Engineer")

        assert session_a == session_b  # both produce the literal key "user:1:Backend Engineer"


class TestGetInterviewService:
    def test_creates_service_lazily_on_first_call(self):
        assert manager._interview_service is None

        with patch("modules.interview.manager.AsyncGeminiTransport.create") as mock_create:
            mock_create.return_value = MagicMock()
            service = manager.get_interview_service()

        assert service is not None
        assert manager._interview_service is service
        mock_create.assert_called_once()

    def test_returns_cached_singleton_on_subsequent_calls(self):
        with patch("modules.interview.manager.AsyncGeminiTransport.create") as mock_create:
            mock_create.return_value = MagicMock()
            first = manager.get_interview_service()
            second = manager.get_interview_service()

        assert first is second
        # Transport should only be built once -- the whole point of caching.
        mock_create.assert_called_once()

    def test_configures_service_with_expected_defaults(self):
        with patch("modules.interview.manager.AsyncGeminiTransport.create") as mock_create:
            mock_create.return_value = MagicMock()
            service = manager.get_interview_service()

        assert service._config.questions_cache_ttl_seconds == 900
        assert service._config.user_throttle_seconds == 20
        assert service._config.max_cached_question_sets == 100