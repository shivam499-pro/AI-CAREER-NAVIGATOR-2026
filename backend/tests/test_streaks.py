import pytest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.streaks import router
from core.middleware import AuthenticatedUser

app = FastAPI()
app.include_router(router, prefix="/streaks")

def _make_user(user_id: str = "user-123") -> AuthenticatedUser:
    user = MagicMock(spec=AuthenticatedUser)
    user.user_id = user_id
    return user


def _override_user(user_id: str = "user-123"):
    """Return a dependency override that injects a fake authenticated user."""
    from core.middleware import get_current_user

    async def _inner():
        return _make_user(user_id)

    app.dependency_overrides[get_current_user] = _inner


def _clear_overrides():
    app.dependency_overrides.clear()


client = TestClient(app)

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TWO_DAYS_AGO = (date.today() - timedelta(days=2)).isoformat()


# ===========================================================================
# GET /streaks/
# ===========================================================================


class TestGetStreak:
    def setup_method(self):
        _override_user()

    def teardown_method(self):
        _clear_overrides()

    @patch("routers.streaks.get_supabase")
    def test_get_streak_returns_existing_data(self, mock_get_supabase):
        """User has existing streak record — all fields returned correctly."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "current_streak": 5,
                    "longest_streak": 10,
                    "last_practice_date": YESTERDAY,
                    "total_sessions": 20,
                }
            ]
        )

        resp = client.get("/streaks/")

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 5
        assert body["longest_streak"] == 10
        assert body["last_practice_date"] == YESTERDAY
        assert body["total_sessions"] == 20

    @patch("routers.streaks.get_supabase")
    def test_get_streak_returns_zeros_when_no_record(self, mock_get_supabase):
        """No DB row for this user — default zero values returned."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        resp = client.get("/streaks/")

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 0
        assert body["longest_streak"] == 0
        assert body["last_practice_date"] is None
        assert body["total_sessions"] == 0

    @patch("routers.streaks.get_supabase")
    def test_get_streak_returns_zeros_when_data_is_none(self, mock_get_supabase):
        """DB response with data=None treated like empty list."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=None
        )

        resp = client.get("/streaks/")

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 0

    @patch("routers.streaks.get_supabase")
    def test_get_streak_raises_500_on_db_exception(self, mock_get_supabase):
        """DB throws — endpoint returns 500."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception(
            "DB connection lost"
        )

        resp = client.get("/streaks/")

        assert resp.status_code == 500
        assert "Failed to fetch streak data" in resp.json()["detail"]


# ===========================================================================
# POST /streaks/update
# ===========================================================================


class TestUpdateStreak:
    def setup_method(self):
        _override_user()

    def teardown_method(self):
        _clear_overrides()

    # ------------------------------------------------------------------
    # New user — no existing record
    # ------------------------------------------------------------------

    @patch("routers.streaks.get_supabase")
    def test_update_creates_new_streak_for_first_time_user(self, mock_get_supabase):
        """No existing row → insert with streak=1 and return first-time message."""
        mock_supabase = mock_get_supabase.return_value
        mock_select = MagicMock(data=[])
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_select
        )
        mock_insert = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            mock_insert
        )

        resp = client.post("/streaks/update")

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 1
        assert body["longest_streak"] == 1
        assert body["total_sessions"] == 1
        assert "Streak started" in body["message"]

        # Verify insert was called
        mock_supabase.table.return_value.insert.assert_called_once()

    # ------------------------------------------------------------------
    # Already practiced today
    # ------------------------------------------------------------------

    @patch("routers.streaks.get_supabase")
    def test_update_returns_same_when_already_practiced_today(self, mock_get_supabase):
        """last_practice_date == today → no DB write, idempotent response."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "current_streak": 3,
                    "longest_streak": 7,
                    "last_practice_date": TODAY,
                    "total_sessions": 15,
                }
            ]
        )

        resp = client.post("/streaks/update")

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 3
        assert "Already practiced today" in body["message"]

        # No update should have been triggered
        mock_supabase.table.return_value.update.assert_not_called()

    # ------------------------------------------------------------------
    # Practiced yesterday → increment streak
    # ------------------------------------------------------------------

    @patch("routers.streaks.get_supabase")
    def test_update_increments_streak_when_practiced_yesterday(self, mock_get_supabase):
        """last_practice_date == yesterday → streak+1, longest updated if needed."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "current_streak": 4,
                    "longest_streak": 4,
                    "last_practice_date": YESTERDAY,
                    "total_sessions": 10,
                }
            ]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.post("/streaks/update")

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 5
        assert body["longest_streak"] == 5  # new record
        assert body["total_sessions"] == 11
        assert "5 day streak" in body["message"]

    @patch("routers.streaks.get_supabase")
    def test_update_does_not_overwrite_longest_if_not_beaten(self, mock_get_supabase):
        """Longest streak stays if current streak doesn't beat it."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "current_streak": 2,
                    "longest_streak": 10,
                    "last_practice_date": YESTERDAY,
                    "total_sessions": 5,
                }
            ]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.post("/streaks/update")

        body = resp.json()
        assert body["current_streak"] == 3
        assert body["longest_streak"] == 10  # preserved

    # ------------------------------------------------------------------
    # Streak broken (last practice older than yesterday)
    # ------------------------------------------------------------------

    @patch("routers.streaks.get_supabase")
    def test_update_resets_streak_when_gap_exists(self, mock_get_supabase):
        """last_practice_date is 2+ days ago → streak resets to 1."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "current_streak": 8,
                    "longest_streak": 8,
                    "last_practice_date": TWO_DAYS_AGO,
                    "total_sessions": 30,
                }
            ]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.post("/streaks/update")

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 1
        assert body["longest_streak"] == 8  # preserved from before
        assert body["total_sessions"] == 31
        assert "Don't break your streak" in body["message"]

    # ------------------------------------------------------------------
    # Edge: last_practice_date is None in existing record
    # ------------------------------------------------------------------

    @patch("routers.streaks.get_supabase")
    def test_update_resets_when_last_practice_date_is_none(self, mock_get_supabase):
        """Existing record but no last_practice_date → treated as broken streak."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "current_streak": 0,
                    "longest_streak": 3,
                    "last_practice_date": None,
                    "total_sessions": 5,
                }
            ]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.post("/streaks/update")

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 1

    # ------------------------------------------------------------------
    # Edge: invalid date string stored in DB
    # ------------------------------------------------------------------

    @patch("routers.streaks.get_supabase")
    def test_update_handles_invalid_date_string_gracefully(self, mock_get_supabase):
        """Corrupt date string in DB → treated as None, streak resets to 1."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "current_streak": 5,
                    "longest_streak": 5,
                    "last_practice_date": "not-a-valid-date",
                    "total_sessions": 10,
                }
            ]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.post("/streaks/update")

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 1

    # ------------------------------------------------------------------
    # Exception path
    # ------------------------------------------------------------------

    @patch("routers.streaks.get_supabase")
    def test_update_returns_500_on_db_exception(self, mock_get_supabase):
        """Any unhandled exception → 500 with descriptive message."""
        mock_supabase = mock_get_supabase.return_value
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception(
            "timeout"
        )

        resp = client.post("/streaks/update")

        assert resp.status_code == 500
        assert "Failed to update streak data" in resp.json()["detail"]