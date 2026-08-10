"""
Coverage-focused tests for routers/interview.py.

tests/integration/contract/test_interview_contract.py already covers the
happy-path response *shapes* the frontend depends on. This file targets the
branches that were still missing: ownership checks (403s), each of the
independent try/except blocks inside save_session (each one must fail
gracefully without breaking the request), the outer save_session error
handler, and the history / progress / question-hint endpoints, which had
no coverage at all.
"""
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from tests.integration.conftest import TEST_USER_ID, make_supabase_response


SAVE_SESSION_PAYLOAD = {
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


class TestOwnershipChecks:
    """user.user_id must match body.user_id / path user_id, or it's a 403."""

    def test_generate_questions_forbidden_for_other_users_body(self, authed_client, mock_supabase):
        response = authed_client.post(
            "/api/v1/interview/generate-questions",
            json={
                "user_id": "someone-else",
                "career_path": "Full Stack Developer",
            },
        )
        assert response.status_code == 403

    def test_evaluate_answer_forbidden_for_other_users_body(self, authed_client, mock_supabase):
        response = authed_client.post(
            "/api/v1/interview/evaluate-answer",
            json={
                "question": "Explain REST vs GraphQL",
                "answer": "REST uses fixed endpoints",
                "career_path": "Full Stack Developer",
                "user_id": "someone-else",
            },
        )
        assert response.status_code == 403

    def test_save_session_forbidden_for_other_users_body(self, authed_client, mock_supabase):
        payload = {**SAVE_SESSION_PAYLOAD, "user_id": "someone-else"}
        response = authed_client.post("/api/v1/interview/save-session", json=payload)
        assert response.status_code == 403

    def test_get_interview_history_forbidden_for_other_users_path(self, authed_client, mock_supabase):
        response = authed_client.get("/api/v1/interview/history/someone-else")
        assert response.status_code == 403

    def test_get_user_progress_forbidden_for_other_users_path(self, authed_client, mock_supabase):
        response = authed_client.get("/api/v1/interview/progress/someone-else")
        assert response.status_code == 403


class TestEvaluateAnswerErrorHandling:
    def test_ai_failure_reasons_return_503_style_500(self, authed_client, mock_supabase):
        """Each of the four recognized failure codes should surface as a 500
        with a friendly 'please retry' message, not the raw error."""
        mock_service = MagicMock()
        mock_service.evaluate_answer = AsyncMock(
            return_value={"success": False, "error": "rate_limit"}
        )

        with patch("routers.interview.get_interview_service", return_value=mock_service):
            response = authed_client.post(
                "/api/v1/interview/evaluate-answer",
                json={
                    "question": "Explain REST vs GraphQL",
                    "answer": "REST uses fixed endpoints",
                    "career_path": "Full Stack Developer",
                    "user_id": TEST_USER_ID,
                },
            )

        assert response.status_code == 500
        assert "try again" in response.json()["detail"].lower()

    def test_unrecognized_failure_reason_still_returns_200(self, authed_client, mock_supabase):
        """A success=False result with an error code NOT in the retry list
        should just be passed through, not converted to a 500."""
        mock_service = MagicMock()
        mock_service.evaluate_answer = AsyncMock(
            return_value={"success": False, "error": "invalid_input"}
        )

        with patch("routers.interview.get_interview_service", return_value=mock_service):
            response = authed_client.post(
                "/api/v1/interview/evaluate-answer",
                json={
                    "question": "Explain REST vs GraphQL",
                    "answer": "REST uses fixed endpoints",
                    "career_path": "Full Stack Developer",
                    "user_id": TEST_USER_ID,
                },
            )

        assert response.status_code == 200
        assert response.json()["error"] == "invalid_input"


class TestSaveSessionResilience:
    """save_session wraps interview-insert, memory-engine, evolution-engine,
    and badge-service in their OWN try/except blocks so a failure in any one
    of them doesn't take down the whole request. Each must be proven independently.
    """

    def _post(self, authed_client):
        return authed_client.post("/api/v1/interview/save-session", json=SAVE_SESSION_PAYLOAD)

    def test_insert_failure_returns_500_not_a_silent_success(self, authed_client, mock_supabase):
        """The core interview_sessions insert failing must surface as a
        real error, not a false 'success: True' with data quietly lost."""
        with patch(
            "routers.interview.interview_module_service.save_session_data",
            new=AsyncMock(side_effect=Exception("insert failed")),
        ):
            response = self._post(authed_client)

        assert response.status_code == 500


    def test_survives_career_memory_engine_failure(self, authed_client, mock_supabase):
        with patch(
            "services.career_memory_engine.update_user_memory",
            side_effect=Exception("memory engine down"),
        ):
            response = self._post(authed_client)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_survives_career_evolution_engine_failure(self, authed_client, mock_supabase):
        with patch(
            "services.career_evolution_engine.update_user_evolution_profile",
            side_effect=Exception("evolution engine down"),
        ):
            response = self._post(authed_client)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_survives_badge_service_failure_and_returns_zeroed_defaults(self, authed_client, mock_supabase):
        with patch(
            "services.badge_service.check_badges_on_session_complete",
            side_effect=Exception("badge service down"),
        ):
            response = self._post(authed_client)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        # badge_result falls back to the zeroed default declared before the try block
        assert body["new_badges"] == []
        assert body["total_xp_earned"] == 0
        assert body["rank_update"] is None

    def test_unexpected_error_outside_inner_blocks_returns_500(self, authed_client, mock_supabase):
        """A failure before/outside the four inner try/excepts (e.g. the
        event loop itself misbehaving) should hit the outer handler."""
        with patch(
            "routers.interview.asyncio.get_event_loop",
            side_effect=RuntimeError("no event loop"),
        ):
            response = self._post(authed_client)

        assert response.status_code == 500
        assert "no event loop" in response.json()["detail"]


class TestGetInterviewHistory:
    def _build_client_mock(self, count_data, page_data, total_count):
        """Mirror the exact chain the router builds:
        count query:  .table().select(..., count=True).eq().execute()
        page query:   .table().select(...).eq().order().range().execute()
        """
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table

        select_mock = MagicMock()
        table.select.return_value = select_mock

        eq_mock = MagicMock()
        select_mock.eq.return_value = eq_mock
        eq_mock.execute.return_value = make_supabase_response(count_data, count=total_count)

        order_mock = MagicMock()
        eq_mock.order.return_value = order_mock
        range_mock = MagicMock()
        order_mock.range.return_value = range_mock
        range_mock.execute.return_value = make_supabase_response(page_data)

        return client

    def test_returns_sessions_with_pagination_metadata(self, authed_client, mock_supabase):
        sessions = [
            {"career_path": "Backend Engineer", "total_score": 8, "created_at": "2026-07-01T00:00:00Z"},
            {"career_path": "Backend Engineer", "total_score": 9, "created_at": "2026-07-02T00:00:00Z"},
        ]
        client_mock = self._build_client_mock(count_data=sessions, page_data=sessions, total_count=2)

        with patch("routers.interview.get_supabase", return_value=client_mock):
            response = authed_client.get(f"/api/v1/interview/history/{TEST_USER_ID}?page=1&limit=10")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert body["pagination"] == {"page": 1, "limit": 10, "total": 2, "total_pages": 1}
        # router reverses page_res.data before returning
        assert body["sessions"] == list(reversed(sessions))

    def test_returns_500_when_database_query_fails(self, authed_client, mock_supabase):
        with patch("routers.interview.get_supabase", side_effect=Exception("db unreachable")):
            response = authed_client.get(f"/api/v1/interview/history/{TEST_USER_ID}")

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve history"


class TestGetQuestionHint:
    def test_returns_hint_from_interview_service(self, authed_client, mock_supabase):
        mock_service = MagicMock()
        mock_service.get_hint = AsyncMock(return_value={"hint": "Talk about tradeoffs."})

        with patch("routers.interview.get_interview_service", return_value=mock_service):
            response = authed_client.post(
                "/api/v1/interview/question-hint",
                json={"question": "Explain REST vs GraphQL", "career_path": "Full Stack Developer"},
            )

        assert response.status_code == 200
        assert response.json() == {"hint": "Talk about tradeoffs."}
        mock_service.get_hint.assert_awaited_once_with(
            question="Explain REST vs GraphQL",
            career_path="Full Stack Developer",
        )


class TestGetUserProgress:
    def _build_client_mock(self, sessions, rank_rows, streak_rows):
        client = MagicMock()

        sessions_table = MagicMock()
        sessions_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            make_supabase_response(sessions)
        )

        ranks_table = MagicMock()
        ranks_table.select.return_value.eq.return_value.execute.return_value = make_supabase_response(rank_rows)

        streaks_table = MagicMock()
        streaks_table.select.return_value.eq.return_value.execute.return_value = make_supabase_response(streak_rows)

        tables = {
            "interview_sessions": sessions_table,
            "user_ranks": ranks_table,
            "user_streaks": streaks_table,
        }
        client.table.side_effect = lambda name: tables[name]
        return client

    def test_returns_sessions_rank_and_streaks_when_data_exists(self, authed_client, mock_supabase):
        sessions = [{"career_path": "Backend Engineer", "total_score": 8, "created_at": "2026-07-01T00:00:00Z"}]
        rank_rows = [{"xp": 250, "level": 3, "rank_title": "🚀 Explorer"}]
        streak_rows = [{"current_streak": 5, "longest_streak": 9, "total_sessions": 12}]
        client_mock = self._build_client_mock(sessions, rank_rows, streak_rows)

        with patch("routers.interview.get_supabase", return_value=client_mock):
            response = authed_client.get(f"/api/v1/interview/progress/{TEST_USER_ID}")

        assert response.status_code == 200
        body = response.json()
        assert body["sessions"] == list(reversed(sessions))
        assert body["rank"] == rank_rows[0]
        assert body["streaks"] == streak_rows[0]

    def test_returns_defaults_when_rank_and_streak_rows_are_missing(self, authed_client, mock_supabase):
        client_mock = self._build_client_mock(sessions=[], rank_rows=[], streak_rows=[])

        with patch("routers.interview.get_supabase", return_value=client_mock):
            response = authed_client.get(f"/api/v1/interview/progress/{TEST_USER_ID}")

        assert response.status_code == 200
        body = response.json()
        assert body["sessions"] == []
        assert body["rank"] == {"xp": 0, "level": 1, "rank_title": "🌱 Fresher"}
        assert body["streaks"] == {"current_streak": 0, "longest_streak": 0, "total_sessions": 0}

    def test_returns_fallback_payload_with_200_on_db_error(self, authed_client, mock_supabase):
        """Unlike history, progress swallows the error and returns a
        200 with safe defaults plus an 'error' field -- this is a
        deliberate design choice worth locking in with a test."""
        with patch("routers.interview.get_supabase", side_effect=Exception("db unreachable")):
            response = authed_client.get(f"/api/v1/interview/progress/{TEST_USER_ID}")

        assert response.status_code == 200
        body = response.json()
        assert body["sessions"] == []
        assert body["rank"] == {"xp": 0, "level": 1, "rank_title": "🌱 Fresher"}
        assert body["streaks"] == {"current_streak": 0, "longest_streak": 0, "total_sessions": 0}
        assert body["error"] == "db unreachable"