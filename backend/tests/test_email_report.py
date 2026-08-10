"""
Tests for routers/email_report.py

Coverage targets: build_weekly_report() pure-function paths, and both
router endpoints (send-report, report-preview) via mocked Supabase.

routers.email_report resolves its Supabase client fresh per-request via
get_supabase() (not a stale module-level import), so these tests patch
"routers.email_report.get_supabase" rather than a bare attribute.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.email_report import router, build_weekly_report
from core.middleware import AuthenticatedUser

app = FastAPI()
app.include_router(router, prefix="/email")


def _make_user(user_id: str = "user-abc") -> AuthenticatedUser:
    return AuthenticatedUser(user_id=user_id, email=f"{user_id}@test.local")


def _override_user(user_id: str = "user-abc"):
    from core.middleware import get_current_user

    async def _inner():
        return _make_user(user_id)

    app.dependency_overrides[get_current_user] = _inner


def _clear_overrides():
    app.dependency_overrides.clear()


client = TestClient(app)


def _make_session(score: int, career: str = "Software Engineering") -> dict:
    return {"total_score": score, "career_path": career}


def _make_streak(current: int = 3) -> dict:
    return {"current_streak": current}


def _make_rank(title: str = "🥈 Junior", xp: int = 500) -> dict:
    return {"rank_title": title, "xp": xp}


# ===========================================================================
# build_weekly_report() — pure function, no mocks needed
# ===========================================================================


class TestBuildWeeklyReport:

    def test_report_with_no_sessions_contains_no_practice_message(self):
        html = build_weekly_report({"sessions": [], "streak": {}, "rank": {}})
        assert "No practice sessions this week" in html
        assert "This Week's Challenge" in html

    def test_report_shows_streak_and_rank_always(self):
        html = build_weekly_report(
            {
                "sessions": [],
                "streak": _make_streak(7),
                "rank": _make_rank("🥇 Senior", 1200),
            }
        )
        assert "7 day" in html
        assert "🥇 Senior" in html
        assert "1200 XP" in html

    def test_report_streak_singular_vs_plural(self):
        html_one = build_weekly_report(
            {"sessions": [], "streak": _make_streak(1), "rank": {}}
        )
        html_two = build_weekly_report(
            {"sessions": [], "streak": _make_streak(2), "rank": {}}
        )
        assert "1 day<" in html_one
        assert "2 days" in html_two

    def test_report_with_sessions_shows_best_score(self):
        sessions = [
            _make_session(30, "Data Science"),
            _make_session(45, "Backend Engineering"),
            _make_session(20, "Frontend"),
        ]
        html = build_weekly_report(
            {"sessions": sessions, "streak": _make_streak(2), "rank": _make_rank()}
        )
        assert "45/50" in html
        assert "Backend Engineering" in html

    def test_report_avg_score_above_40_gives_crushing_it_tip(self):
        sessions = [_make_session(45), _make_session(42)]
        html = build_weekly_report({"sessions": sessions, "streak": {}, "rank": {}})
        assert "crushing it" in html

    def test_report_avg_score_between_25_and_40_gives_solid_progress_tip(self):
        sessions = [_make_session(30), _make_session(28)]
        html = build_weekly_report({"sessions": sessions, "streak": {}, "rank": {}})
        assert "Solid progress" in html

    def test_report_avg_score_below_25_gives_consistency_tip(self):
        sessions = [_make_session(10), _make_session(15)]
        html = build_weekly_report({"sessions": sessions, "streak": {}, "rank": {}})
        assert "Consistency beats talent" in html

    def test_report_shows_weakest_career_area(self):
        sessions = [
            _make_session(45, "Backend"),
            _make_session(10, "System Design"),
            _make_session(8, "System Design"),
        ]
        html = build_weekly_report({"sessions": sessions, "streak": {}, "rank": {}})
        assert "System Design" in html

    def test_report_shows_average_score(self):
        sessions = [_make_session(30), _make_session(20)]
        html = build_weekly_report({"sessions": sessions, "streak": {}, "rank": {}})
        assert "25.0/50" in html

    def test_report_uses_defaults_when_streak_and_rank_missing(self):
        html = build_weekly_report({"sessions": [], "streak": {}, "rank": {}})
        assert "🌱 Fresher" in html
        assert "0 XP" in html

    def test_report_single_session_still_works(self):
        html = build_weekly_report(
            {
                "sessions": [_make_session(35, "ML Engineering")],
                "streak": _make_streak(1),
                "rank": _make_rank(),
            }
        )
        assert "35/50" in html
        assert "35.0/50" in html


# ===========================================================================
# POST /email/send-report
# ===========================================================================


class TestSendWeeklyReport:
    def setup_method(self):
        _override_user()

    def teardown_method(self):
        _clear_overrides()

    def _supabase_returns_empty(self, mock_supabase):
        empty = MagicMock(data=[])
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = empty
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    @patch("routers.email_report.get_supabase")
    @patch.dict("os.environ", {}, clear=True)
    def test_send_report_fails_when_gmail_not_configured(self, mock_get_supabase):
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        self._supabase_returns_empty(mock_supabase)

        resp = client.post("/email/send-report", json={"email": "user@example.com"})

        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert "GMAIL_USER" in detail or "Email not configured" in detail

    @patch("routers.email_report.smtplib.SMTP")
    @patch("routers.email_report.get_supabase")
    @patch.dict("os.environ", {"GMAIL_USER": "bot@gmail.com", "GMAIL_APP_PASSWORD": "secret"})
    def test_send_report_succeeds_with_valid_smtp_config(self, mock_get_supabase, mock_smtp_cls):
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        self._supabase_returns_empty(mock_supabase)

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        resp = client.post("/email/send-report", json={"email": "user@example.com"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "user@example.com" in body["message"]

    @patch("routers.email_report.smtplib.SMTP")
    @patch("routers.email_report.get_supabase")
    @patch.dict("os.environ", {"GMAIL_USER": "bot@gmail.com", "GMAIL_APP_PASSWORD": "secret"})
    def test_send_report_returns_500_on_smtp_exception(self, mock_get_supabase, mock_smtp_cls):
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        self._supabase_returns_empty(mock_supabase)
        mock_smtp_cls.side_effect = Exception("Connection refused")

        resp = client.post("/email/send-report", json={"email": "user@example.com"})

        assert resp.status_code == 500
        assert "Failed to send report" in resp.json()["detail"]

    @patch("routers.email_report.get_supabase")
    @patch.dict("os.environ", {"GMAIL_USER": "bot@gmail.com", "GMAIL_APP_PASSWORD": "secret"})
    def test_send_report_returns_500_on_supabase_exception(self, mock_get_supabase):
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = Exception("DB error")

        resp = client.post("/email/send-report", json={"email": "user@example.com"})

        assert resp.status_code == 500

    @patch("routers.email_report.smtplib.SMTP")
    @patch("routers.email_report.get_supabase")
    @patch.dict("os.environ", {"GMAIL_USER": "bot@gmail.com", "GMAIL_APP_PASSWORD": "secret"})
    def test_send_report_fetches_sessions_streak_and_rank(self, mock_get_supabase, mock_smtp_cls):
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        sessions_data = MagicMock(data=[_make_session(40)])
        streak_data = MagicMock(data=[_make_streak(5)])
        rank_data = MagicMock(data=[_make_rank()])

        def side_effect(table_name):
            tbl = MagicMock()
            if table_name == "interview_sessions":
                tbl.select.return_value.eq.return_value.gte.return_value.execute.return_value = sessions_data
            elif table_name == "user_streaks":
                tbl.select.return_value.eq.return_value.execute.return_value = streak_data
            elif table_name == "user_ranks":
                tbl.select.return_value.eq.return_value.execute.return_value = rank_data
            return tbl

        mock_supabase.table.side_effect = side_effect

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        resp = client.post("/email/send-report", json={"email": "user@example.com"})

        assert resp.status_code == 200


# ===========================================================================
# GET /email/report-preview
# ===========================================================================


class TestGetReportPreview:
    def setup_method(self):
        _override_user()

    def teardown_method(self):
        _clear_overrides()

    def _supabase_returns_empty(self, mock_supabase):
        empty = MagicMock(data=[])
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = empty
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    @patch("routers.email_report.get_supabase")
    def test_preview_returns_html_string(self, mock_get_supabase):
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        self._supabase_returns_empty(mock_supabase)

        resp = client.get("/email/report-preview")

        assert resp.status_code == 200
        body = resp.json()
        assert "html" in body
        assert "<!DOCTYPE html>" in body["html"]

    @patch("routers.email_report.get_supabase")
    def test_preview_returns_500_on_exception(self, mock_get_supabase):
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = Exception("timeout")

        resp = client.get("/email/report-preview")

        assert resp.status_code == 500
        assert "Failed to generate preview" in resp.json()["detail"]

    @patch("routers.email_report.get_supabase")
    def test_preview_uses_session_data_to_build_html(self, mock_get_supabase):
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        def side_effect(table_name):
            tbl = MagicMock()
            if table_name == "interview_sessions":
                tbl.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
                    data=[_make_session(48, "AI/ML")]
                )
            else:
                tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            return tbl

        mock_supabase.table.side_effect = side_effect

        resp = client.get("/email/report-preview")

        assert resp.status_code == 200