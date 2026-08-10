"""
Tests for routers/challenges.py.

Note: this router uses the legacy eager `supabase` singleton import, same as
weekly_challenge.py — tests patch `routers.challenges.supabase` directly.

Caution: create_challenge() has a `while existing.data:` retry loop for
challenge-code collisions. A carelessly configured mock that always returns
truthy `.data` will make the loop spin forever. Tests that don't care about
the collision path explicitly set `.data = []` so the loop never runs.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.challenges import router
from core.middleware import get_current_user, AuthenticatedUser


# ─── Test App Setup ───────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router, prefix="/api/v1/challenges")


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


# ─── 1. POST /create ──────────────────────────────────────────────────────────

class TestCreateChallenge:

    _UNSET = object()

    def _mock_no_collision(self, profile_data=None, insert_data=_UNSET):
        mock_sb = MagicMock()

        def table_dispatch(table_name):
            m = MagicMock()
            if table_name == "challenges":
                # No code collision -> loop runs zero times
                m.select.return_value.eq.return_value.execute.return_value.data = []
                m.insert.return_value.execute.return_value.data = (
                    [{"id": 1}] if insert_data is self._UNSET else insert_data
                )
            elif table_name == "profiles":
                m.select.return_value.eq.return_value.execute.return_value.data = profile_data or []
            return m

        mock_sb.table.side_effect = table_dispatch
        return mock_sb

    def test_create_success_with_full_name(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = self._mock_no_collision(profile_data=[{"full_name": "Jane Doe", "email": "jane@test.com"}])

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/create", json={
                "career_path": "Backend Engineer", "questions": [{"q": "..."}]
            })

        assert response.status_code == 200
        body = response.json()
        assert body["creator_name"] == "Jane Doe"
        assert len(body["challenge_code"]) == 8
        assert "share_url" in body

    def test_create_falls_back_to_email_username_when_no_full_name(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = self._mock_no_collision(profile_data=[{"full_name": None, "email": "jane@test.com"}])

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/create", json={
                "career_path": "Backend Engineer", "questions": []
            })

        assert response.status_code == 200
        assert response.json()["creator_name"] == "jane"

    def test_create_defaults_to_anonymous_when_profile_lookup_fails(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()

        def table_dispatch(table_name):
            m = MagicMock()
            if table_name == "challenges":
                m.select.return_value.eq.return_value.execute.return_value.data = []
                m.insert.return_value.execute.return_value.data = [{"id": 1}]
            elif table_name == "profiles":
                m.select.return_value.eq.return_value.execute.side_effect = Exception("profiles down")
            return m
        mock_sb.table.side_effect = table_dispatch

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/create", json={
                "career_path": "Backend Engineer", "questions": []
            })

        assert response.status_code == 200
        assert response.json()["creator_name"] == "Anonymous"

    def test_create_retries_on_challenge_code_collision(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        table_mocks = {}

        def table_dispatch(table_name):
            if table_name in table_mocks:
                return table_mocks[table_name]
            m = MagicMock()
            if table_name == "challenges":
                # First check: collision (truthy data) -> loop runs once.
                # Second check: no collision -> loop exits.
                # Memoized so both checks (and the later insert) share this
                # same mock instance and its 2-item side_effect iterator.
                m.select.return_value.eq.return_value.execute.side_effect = [
                    MagicMock(data=[{"challenge_code": "COLLIDE1"}]),
                    MagicMock(data=[]),
                ]
                m.insert.return_value.execute.return_value.data = [{"id": 1}]
            elif table_name == "profiles":
                m.select.return_value.eq.return_value.execute.return_value.data = []
            table_mocks[table_name] = m
            return m
        mock_sb.table.side_effect = table_dispatch

        with patch("routers.challenges.supabase", mock_sb), \
             patch("routers.challenges.generate_challenge_code", side_effect=["COLLIDE1", "UNIQUE01"]):
            response = client.post("/api/v1/challenges/create", json={
                "career_path": "Backend Engineer", "questions": []
            })

        assert response.status_code == 200
        assert response.json()["challenge_code"] == "UNIQUE01"

    def test_create_insert_failure_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = self._mock_no_collision(insert_data=None)

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/create", json={
                "career_path": "Backend Engineer", "questions": []
            })

        assert response.status_code == 500
        assert "Failed to create challenge" in response.json()["detail"]

    def test_create_unexpected_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("db down")

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/create", json={
                "career_path": "Backend Engineer", "questions": []
            })

        assert response.status_code == 500


# ─── 2. GET /{challenge_code} ─────────────────────────────────────────────────

class TestGetChallenge:

    def test_challenge_found(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "challenge_code": "ABCD1234", "career_path": "Backend Engineer",
            "questions": [{"q": "..."}], "creator_name": "Jane"
        }]

        with patch("routers.challenges.supabase", mock_sb):
            response = client.get("/api/v1/challenges/abcd1234")

        assert response.status_code == 200
        assert response.json()["challenge_code"] == "ABCD1234"

    def test_challenge_code_is_uppercased_before_lookup(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "challenge_code": "ABCD1234", "career_path": "X", "questions": []
        }]

        with patch("routers.challenges.supabase", mock_sb):
            client.get("/api/v1/challenges/abcd1234")

        eq_call = mock_sb.table.return_value.select.return_value.eq.call_args
        assert eq_call.args == ("challenge_code", "ABCD1234")

    def test_challenge_not_found_returns_404(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with patch("routers.challenges.supabase", mock_sb):
            response = client.get("/api/v1/challenges/nonexistent")

        assert response.status_code == 404

    def test_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("boom")

        with patch("routers.challenges.supabase", mock_sb):
            response = client.get("/api/v1/challenges/abcd1234")

        assert response.status_code == 500


# ─── 3. POST /submit ──────────────────────────────────────────────────────────

class TestSubmitChallengeResult:

    def _mock_sb(self, profile_data=None, leaderboard_rows=None):
        mock_sb = MagicMock()
        table_mocks = {}

        def table_dispatch(table_name):
            if table_name in table_mocks:
                return table_mocks[table_name]
            m = MagicMock()
            if table_name == "profiles":
                m.select.return_value.eq.return_value.execute.return_value.data = profile_data or []
            elif table_name == "challenge_results":
                m.select.return_value.eq.return_value.order.return_value.execute.return_value.data = (
                    leaderboard_rows or []
                )
            table_mocks[table_name] = m
            return m
        mock_sb.table.side_effect = table_dispatch
        return mock_sb

    def test_submit_success_with_full_name(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = self._mock_sb(
            profile_data=[{"full_name": "Jane Doe", "email": "jane@test.com"}],
            leaderboard_rows=[{"user_name": "Jane Doe", "user_email": "jane@test.com", "score": 90, "completed_at": "now"}],
        )

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/submit", json={
                "challenge_code": "abcd1234", "score": 90, "answers": ["a"]
            })

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["leaderboard"][0]["user_name"] == "Jane Doe"

    def test_submit_uses_email_username_when_no_full_name(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = self._mock_sb(
            profile_data=[{"full_name": None, "email": "bob@test.com"}],
            leaderboard_rows=[],
        )

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/submit", json={
                "challenge_code": "abcd1234", "score": 50, "answers": []
            })

        assert response.status_code == 200
        insert_call = mock_sb.table("challenge_results").insert.call_args.args[0]
        assert insert_call["user_name"] == "bob"

    def test_submit_defaults_to_anonymous_on_profile_failure(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()

        def table_dispatch(table_name):
            m = MagicMock()
            if table_name == "profiles":
                m.select.return_value.eq.return_value.execute.side_effect = Exception("down")
            elif table_name == "challenge_results":
                m.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return m
        mock_sb.table.side_effect = table_dispatch

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/submit", json={
                "challenge_code": "abcd1234", "score": 10, "answers": []
            })

        assert response.status_code == 200

    def test_submit_uppercases_challenge_code(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = self._mock_sb(profile_data=[], leaderboard_rows=[])

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/submit", json={
                "challenge_code": "abcd1234", "score": 10, "answers": []
            })

        assert response.status_code == 200
        insert_call = mock_sb.table("challenge_results").insert.call_args.args[0]
        assert insert_call["challenge_code"] == "ABCD1234"

    def test_unexpected_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("db down")

        with patch("routers.challenges.supabase", mock_sb):
            response = client.post("/api/v1/challenges/submit", json={
                "challenge_code": "abcd1234", "score": 10, "answers": []
            })

        assert response.status_code == 500


# ─── 4. GET /leaderboard/{challenge_code} ─────────────────────────────────────

class TestGetLeaderboard:

    def test_returns_paginated_leaderboard_with_ranks(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.count = 2
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
            {"user_name": "Jane", "user_email": "jane@test.com", "score": 90, "completed_at": "t1"},
            {"user_name": "Bob", "user_email": "bob@test.com", "score": 80, "completed_at": "t2"},
        ]

        with patch("routers.challenges.supabase", mock_sb):
            response = client.get("/api/v1/challenges/leaderboard/abcd1234")

        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total"] == 2
        assert body["leaderboard"][0]["rank"] == 1
        assert body["leaderboard"][1]["rank"] == 2

    def test_second_page_rank_offset_is_correct(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.count = 15
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
            {"user_name": "User11", "user_email": "u11@test.com", "score": 50, "completed_at": "t"},
        ]

        with patch("routers.challenges.supabase", mock_sb):
            response = client.get("/api/v1/challenges/leaderboard/abcd1234?page=2&limit=10")

        assert response.status_code == 200
        body = response.json()
        # page 2, limit 10 -> first row on this page is absolute rank 11
        assert body["leaderboard"][0]["rank"] == 11
        assert body["pagination"]["total_pages"] == 2

    def test_empty_leaderboard(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.count = 0
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []

        with patch("routers.challenges.supabase", mock_sb):
            response = client.get("/api/v1/challenges/leaderboard/abcd1234")

        assert response.status_code == 200
        body = response.json()
        assert body["leaderboard"] == []
        assert body["pagination"]["total"] == 0

    def test_exception_returns_500(self):
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("boom")

        with patch("routers.challenges.supabase", mock_sb):
            response = client.get("/api/v1/challenges/leaderboard/abcd1234")

        assert response.status_code == 500