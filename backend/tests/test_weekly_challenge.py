"""
Tests for routers/weekly_challenge.py.

Note: this router still uses the legacy eager `supabase` singleton import
(`from core.supabase_client import supabase`), not the lazy get_supabase()
pattern used by streaks/badges/interview — so tests here correctly patch
`routers.weekly_challenge.supabase` directly, matching current code.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.weekly_challenge import router
from core.middleware import get_current_user, AuthenticatedUser


# ─── Test App Setup ───────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router, prefix="/api/v1/weekly-challenge")


def make_mock_user(user_id: str = "test-user-123") -> AuthenticatedUser:
    return AuthenticatedUser(user_id=user_id, email="test@test.com", role="user")


def override_auth(user_id: str = "test-user-123"):
    def _override():
        return make_mock_user(user_id)
    return _override


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


WEEK_INFO = (28, 2026, MagicMock(isoformat=lambda: "2026-07-06T00:00:00"),
             MagicMock(isoformat=lambda: "2026-07-12T00:00:00"))


# ─── 1. GET /current ──────────────────────────────────────────────────────────

class TestGetCurrentWeekChallenge:

    def test_challenge_already_exists_returns_it(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{
            "week_number": 28, "year": 2026, "theme": "Graphs",
            "career_path": "Backend Engineer", "questions": [{"q": "..."}],
            "starts_at": "2026-07-06", "ends_at": "2026-07-12"
        }]

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO):
            response = client.get("/api/v1/weekly-challenge/current")

        assert response.status_code == 200
        body = response.json()
        assert body["theme"] == "Graphs"
        assert body["week_number"] == 28

    def test_challenge_missing_creates_new_one(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": 1}]

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO):
            response = client.get("/api/v1/weekly-challenge/current")

        assert response.status_code == 200
        body = response.json()
        assert body["theme"] == "Data Structures & Algorithms"
        assert body["week_number"] == 28
        mock_sb.table.return_value.insert.assert_called_once()

    def test_challenge_creation_fails_returns_500(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = None

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO):
            response = client.get("/api/v1/weekly-challenge/current")

        assert response.status_code == 500

    def test_unexpected_exception_returns_500(self):
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("db down")

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.get("/api/v1/weekly-challenge/current")

        assert response.status_code == 500


# ─── 2. POST /submit ──────────────────────────────────────────────────────────

class TestSubmitWeeklyChallenge:

    def _base_supabase_mock(self, leaderboard_rows=None, existing_submission=None, profile_email=None):
        """Build a mock supabase client whose .table() dispatches based on the
        table name argument, since /submit hits 3 different tables. Mocks are
        memoized per table name so call assertions (e.g. .update.assert_called)
        made after the request still see the same object the router touched."""
        mock_sb = MagicMock()
        table_mocks = {}

        def table_dispatch(table_name):
            if table_name in table_mocks:
                return table_mocks[table_name]

            m = MagicMock()
            if table_name == "profiles":
                m.select.return_value.eq.return_value.execute.return_value.data = (
                    [{"email": profile_email}] if profile_email else []
                )
            elif table_name == "weekly_results":
                # existing-submission check (3 chained .eq())
                m.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
                    existing_submission or []
                )
                # leaderboard fetch (2 chained .eq() then .order())
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = (
                    leaderboard_rows or []
                )
            table_mocks[table_name] = m
            return m

        mock_sb.table.side_effect = table_dispatch
        return mock_sb

    def test_first_time_submission_creates_result(self):
        app.dependency_overrides[get_current_user] = override_auth("user-1")
        mock_sb = self._base_supabase_mock(
            leaderboard_rows=[{"user_id": "user-1", "user_email": "a@test.com", "score": 80, "completed_at": "now"}],
            profile_email="a@test.com",
        )

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO), \
             patch("services.badge_service.check_and_award_badges") as mock_badges:
            mock_badges.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}

            response = client.post("/api/v1/weekly-challenge/submit", json={
                "score": 80, "answers": ["a", "b"], "is_voice": False
            })

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["rank"] == 1

    def test_higher_score_updates_existing_submission(self):
        app.dependency_overrides[get_current_user] = override_auth("user-1")
        mock_sb = self._base_supabase_mock(
            existing_submission=[{"id": 55, "score": 40}],
            leaderboard_rows=[{"user_id": "user-1", "user_email": "a@test.com", "score": 90, "completed_at": "now"}],
        )

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO), \
             patch("services.badge_service.check_and_award_badges") as mock_badges:
            mock_badges.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}

            response = client.post("/api/v1/weekly-challenge/submit", json={
                "score": 90, "answers": ["a"], "is_voice": False
            })

        assert response.status_code == 200
        weekly_results_mock = mock_sb.table("weekly_results")
        weekly_results_mock.update.assert_called_once()
        updated_fields = weekly_results_mock.update.call_args.args[0]
        assert updated_fields["score"] == 90

    def test_lower_score_does_not_overwrite_existing_submission(self):
        app.dependency_overrides[get_current_user] = override_auth("user-1")
        mock_sb = self._base_supabase_mock(
            existing_submission=[{"id": 55, "score": 95}],
            leaderboard_rows=[{"user_id": "user-1", "user_email": "a@test.com", "score": 95, "completed_at": "now"}],
        )

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO), \
             patch("services.badge_service.check_and_award_badges") as mock_badges:
            mock_badges.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}

            response = client.post("/api/v1/weekly-challenge/submit", json={
                "score": 10, "answers": [], "is_voice": False
            })

        assert response.status_code == 200
        # Score of 10 is not > existing 95, so .update() must never be called
        weekly_results_mock = mock_sb.table("weekly_results")
        weekly_results_mock.update.assert_not_called()

    def test_rank_and_winner_matched_only_by_user_id_not_email(self):
        """Regression test for the fixed bug: two 'Anonymous' users must not
        collide on rank/winner status — only user_id determines a match."""
        app.dependency_overrides[get_current_user] = override_auth("user-1")
        mock_sb = self._base_supabase_mock(
            # profile lookup fails -> current user's email falls back to "Anonymous"
            profile_email=None,
            leaderboard_rows=[
                {"user_id": "someone-else", "user_email": "Anonymous", "score": 100, "completed_at": "now"},
                {"user_id": "user-1", "user_email": "Anonymous", "score": 50, "completed_at": "now"},
            ],
        )

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO), \
             patch("services.badge_service.check_and_award_badges") as mock_badges:
            mock_badges.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}

            response = client.post("/api/v1/weekly-challenge/submit", json={
                "score": 50, "answers": [], "is_voice": False
            })

        assert response.status_code == 200
        body = response.json()
        # user-1 is rank 2 (their own row), NOT rank 1 (the other Anonymous user)
        assert body["rank"] == 2
        # challenge_won must only be checked for the true #1, so only one
        # check_and_award_badges call (session_complete), not a winner check
        events_checked = [call.kwargs.get("event") for call in mock_badges.call_args_list]
        assert "challenge_won" not in events_checked

    def test_winner_gets_challenge_won_badge_check(self):
        app.dependency_overrides[get_current_user] = override_auth("user-1")
        mock_sb = self._base_supabase_mock(
            profile_email="a@test.com",
            leaderboard_rows=[{"user_id": "user-1", "user_email": "a@test.com", "score": 100, "completed_at": "now"}],
        )

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO), \
             patch("services.badge_service.check_and_award_badges") as mock_badges:
            mock_badges.side_effect = [
                {"new_badges": ["first_session"], "total_xp_earned": 10, "rank_update": None},
                {"new_badges": ["weekly_winner"], "total_xp_earned": 50, "rank_update": None},
            ]

            response = client.post("/api/v1/weekly-challenge/submit", json={
                "score": 100, "answers": [], "is_voice": False
            })

        assert response.status_code == 200
        body = response.json()
        assert set(body["new_badges"]) == {"first_session", "weekly_winner"}
        assert body["total_xp_earned"] == 60
        events_checked = [call.kwargs.get("event") for call in mock_badges.call_args_list]
        assert "challenge_won" in events_checked

    def test_badge_service_failure_is_non_fatal(self):
        app.dependency_overrides[get_current_user] = override_auth("user-1")
        mock_sb = self._base_supabase_mock(
            profile_email="a@test.com",
            leaderboard_rows=[{"user_id": "user-1", "user_email": "a@test.com", "score": 100, "completed_at": "now"}],
        )

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO), \
             patch("services.badge_service.check_and_award_badges") as mock_badges:
            mock_badges.side_effect = Exception("badge service down")

            response = client.post("/api/v1/weekly-challenge/submit", json={
                "score": 100, "answers": [], "is_voice": False
            })

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["new_badges"] == []

    def test_profile_lookup_failure_defaults_to_anonymous(self):
        app.dependency_overrides[get_current_user] = override_auth("user-1")
        mock_sb = MagicMock()

        def table_dispatch(table_name):
            m = MagicMock()
            if table_name == "profiles":
                m.select.return_value.eq.return_value.execute.side_effect = Exception("profiles table down")
            elif table_name == "weekly_results":
                m.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    {"user_id": "user-1", "user_email": "Anonymous", "score": 20, "completed_at": "now"}
                ]
            return m
        mock_sb.table.side_effect = table_dispatch

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO), \
             patch("services.badge_service.check_and_award_badges") as mock_badges:
            mock_badges.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}

            response = client.post("/api/v1/weekly-challenge/submit", json={
                "score": 20, "answers": [], "is_voice": False
            })

        # A failed profile lookup must not fail the whole submission
        assert response.status_code == 200

    def test_unexpected_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("total outage")

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.post("/api/v1/weekly-challenge/submit", json={
                "score": 10, "answers": [], "is_voice": False
            })

        assert response.status_code == 500


# ─── 3. GET /leaderboard ──────────────────────────────────────────────────────

class TestGetWeeklyLeaderboard:

    def test_returns_ranked_leaderboard(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"user_email": "a@test.com", "score": 90, "completed_at": "t1"},
            {"user_email": "b@test.com", "score": 80, "completed_at": "t2"},
        ]

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO):
            response = client.get("/api/v1/weekly-challenge/leaderboard")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["rank"] == 1
        assert body[1]["rank"] == 2

    def test_empty_leaderboard_returns_empty_list(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        with patch("routers.weekly_challenge.supabase", mock_sb), \
             patch("routers.weekly_challenge.get_current_week_info", return_value=WEEK_INFO):
            response = client.get("/api/v1/weekly-challenge/leaderboard")

        assert response.status_code == 200
        assert response.json() == []

    def test_exception_returns_500(self):
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("db down")

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.get("/api/v1/weekly-challenge/leaderboard")

        assert response.status_code == 500


# ─── 4. POST /start ───────────────────────────────────────────────────────────

class TestStartWeeklyChallenge:

    def test_existing_attempt_is_returned(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": 7, "status": "in_progress"}
        ]

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.post("/api/v1/weekly-challenge/start", json={"week_number": 28, "year": 2026})

        assert response.status_code == 200
        body = response.json()
        assert body["attempt_id"] == 7
        assert body["status"] == "in_progress"

    def test_no_existing_attempt_creates_new_one(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": 9}]

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.post("/api/v1/weekly-challenge/start", json={"week_number": 28, "year": 2026})

        assert response.status_code == 200
        body = response.json()
        assert body["attempt_id"] == 9
        assert body["status"] == "started"

    def test_insert_failure_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = None

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.post("/api/v1/weekly-challenge/start", json={"week_number": 28, "year": 2026})

        assert response.status_code == 500

    def test_unexpected_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("boom")

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.post("/api/v1/weekly-challenge/start", json={"week_number": 28, "year": 2026})

        assert response.status_code == 500


# ─── 5. GET /attempt ──────────────────────────────────────────────────────────

class TestGetAttemptStatus:

    def test_existing_attempt_found(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": 3, "status": "completed"}
        ]

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.get("/api/v1/weekly-challenge/attempt?week_number=28&year=2026")

        assert response.status_code == 200
        body = response.json()
        assert body["exists"] is True
        assert body["status"] == "completed"
        assert body["attempt_id"] == 3

    def test_no_attempt_found(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.get("/api/v1/weekly-challenge/attempt?week_number=28&year=2026")

        assert response.status_code == 200
        body = response.json()
        assert body["exists"] is False
        assert body["status"] == "none"

    def test_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("boom")

        with patch("routers.weekly_challenge.supabase", mock_sb):
            response = client.get("/api/v1/weekly-challenge/attempt?week_number=28&year=2026")

        assert response.status_code == 500