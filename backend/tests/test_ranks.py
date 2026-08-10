"""
Tests for routers/ranks.py

Both endpoints require Depends(get_current_user), and /update derives
user_id from the verified token — never from the request body.

routers.ranks resolves its Supabase client fresh on each request via
core.supabase_client.get_supabase() (not a module-level singleton bound
at import time), so these tests patch "routers.ranks.get_supabase" per
call rather than patching a module attribute directly.
"""
import os

os.environ.setdefault("SUPABASE_URL", "https://fake-test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-key")

from contextlib import contextmanager

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.ranks import router, get_level_info, calculate_xp_earned, LEVELS
from core.middleware import get_current_user, AuthenticatedUser

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _qres(data):
    r = MagicMock()
    r.data = data
    return r


@contextmanager
def _authed_as(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        user_id=user_id, email=f"{user_id}@test.local"
    )
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ─── get_level_info — pure function, the core domain logic ───────────────────

@pytest.mark.parametrize("xp,expected_level,expected_title", [
    (0, 1, "Fresher"), (99, 1, "Fresher"), (100, 2, "Beginner"),
    (249, 2, "Beginner"), (250, 3, "Junior"), (899, 4, "Mid-level"),
    (900, 5, "Senior"), (2000, 7, "Legend"), (5000, 7, "Legend"),
])
def test_get_level_info_boundaries(xp, expected_level, expected_title):
    info = get_level_info(xp)
    assert info["level"] == expected_level
    assert info["title"] == expected_title


def test_get_level_info_progress_percent_is_correct():
    info = get_level_info(300)
    assert info["level"] == 3
    assert info["progress_percent"] == 20.0


def test_get_level_info_progress_percent_correct_for_level_1():
    info = get_level_info(50)
    assert info["level"] == 1
    assert 45 < info["progress_percent"] < 55


def test_get_level_info_progress_percent_at_max_level_does_not_exceed_100():
    info = get_level_info(2000)
    assert info["progress_percent"] == 0
    assert info["next_level_xp"] == 2000


def test_get_level_info_progress_percent_never_negative_or_over_100():
    for xp in [0, 1, 99, 100, 500, 899, 900, 2000, 10000]:
        info = get_level_info(xp)
        assert 0 <= info["progress_percent"] <= 100


def test_levels_table_is_internally_consistent():
    for i, entry in enumerate(LEVELS):
        assert entry["level"] == i + 1
    for i in range(1, len(LEVELS)):
        assert LEVELS[i]["xp_required"] > LEVELS[i - 1]["xp_required"]


# ─── calculate_xp_earned — pure function ──────────────────────────────────────

@pytest.mark.parametrize("score,expected_xp", [
    (0, 10), (39.9, 10), (40, 20), (59.9, 20),
    (60, 35), (79.9, 35), (80, 50), (100, 50),
])
def test_calculate_xp_earned_score_bands(score, expected_xp):
    assert calculate_xp_earned(score) == expected_xp


# ─── GET /{user_id} ────────────────────────────────────────────────────────────

def test_get_rank_returns_default_when_no_record_exists():
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = _qres([])

    with patch("routers.ranks.get_supabase", return_value=fake_supabase), _authed_as("user-new"):
        resp = client.get("/user-new")

    assert resp.status_code == 200
    assert resp.json() == {
        "xp": 0, "level": 1, "rank_title": "🌱 Fresher",
        "next_level_xp": 100, "progress_percent": 0,
    }


def test_get_rank_returns_computed_level_for_existing_record():
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = \
        _qres([{"user_id": "user-A", "xp": 300}])

    with patch("routers.ranks.get_supabase", return_value=fake_supabase), _authed_as("user-A"):
        resp = client.get("/user-A")

    body = resp.json()
    assert body["xp"] == 300
    assert body["level"] == 3
    assert body["rank_title"] == "💼 Junior"


def test_get_rank_supabase_error_returns_500_without_leaking_detail():
    fake_supabase = MagicMock()
    fake_supabase.table.side_effect = Exception("connection refused: internal-db-host:5432")

    with patch("routers.ranks.get_supabase", return_value=fake_supabase), _authed_as("user-A"):
        resp = client.get("/user-A")

    assert resp.status_code == 500
    assert "internal-db-host" not in resp.text
    assert resp.json()["detail"] == "Failed to fetch rank data"


def test_get_rank_requires_authentication():
    resp = client.get("/some-users-id")
    assert resp.status_code == 401


def test_cannot_read_another_users_rank_even_when_authenticated():
    with _authed_as("user-A"):
        resp = client.get("/some-other-users-id")
    assert resp.status_code == 403


# ─── POST /update ──────────────────────────────────────────────────────────────

def test_update_rank_creates_new_record_when_none_exists():
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = _qres([])
    insert_mock = fake_supabase.table.return_value.insert

    with patch("routers.ranks.get_supabase", return_value=fake_supabase), _authed_as("user-new"):
        resp = client.post("/update", json={"score": 85})

    assert resp.status_code == 200
    body = resp.json()
    assert body["xp"] == 50
    assert body["leveled_up"] is False
    insert_mock.assert_called_once()
    assert insert_mock.call_args[0][0]["user_id"] == "user-new"


def test_update_rank_accumulates_xp_on_existing_record():
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = \
        _qres([{"user_id": "user-A", "xp": 60}])
    update_mock = fake_supabase.table.return_value.update

    with patch("routers.ranks.get_supabase", return_value=fake_supabase), _authed_as("user-A"):
        resp = client.post("/update", json={"score": 90})

    body = resp.json()
    assert body["xp"] == 110
    update_mock.assert_called_once()
    assert update_mock.call_args[0][0]["xp"] == 110


def test_update_rank_detects_level_up_crossing_a_boundary():
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = \
        _qres([{"user_id": "user-A", "xp": 90}])

    with patch("routers.ranks.get_supabase", return_value=fake_supabase), _authed_as("user-A"):
        resp = client.post("/update", json={"score": 85})

    body = resp.json()
    assert body["xp"] == 140
    assert body["level"] == 2
    assert body["leveled_up"] is True


def test_update_rank_no_level_up_when_staying_within_same_level():
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = \
        _qres([{"user_id": "user-A", "xp": 100}])

    with patch("routers.ranks.get_supabase", return_value=fake_supabase), _authed_as("user-A"):
        resp = client.post("/update", json={"score": 30})

    body = resp.json()
    assert body["xp"] == 110
    assert body["leveled_up"] is False


def test_update_rank_supabase_error_returns_500_without_leaking_detail():
    fake_supabase = MagicMock()
    fake_supabase.table.side_effect = Exception("duplicate key value violates constraint xyz")

    with patch("routers.ranks.get_supabase", return_value=fake_supabase), _authed_as("user-A"):
        resp = client.post("/update", json={"score": 50})

    assert resp.status_code == 500
    assert "constraint" not in resp.text
    assert resp.json()["detail"] == "Failed to update rank data"


def test_update_rank_requires_authentication():
    resp = client.post("/update", json={"score": 100})
    assert resp.status_code == 401


def test_update_rank_ignores_user_id_in_body_uses_authenticated_identity():
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = _qres([])
    insert_mock = fake_supabase.table.return_value.insert

    with patch("routers.ranks.get_supabase", return_value=fake_supabase), _authed_as("user-A"):
        resp = client.post("/update", json={"user_id": "someone-elses-account", "score": 100})

    assert resp.status_code == 200
    assert insert_mock.call_args[0][0]["user_id"] == "user-A"


def test_update_rank_rejects_missing_required_fields():
    with _authed_as("user-A"):
        resp = client.post("/update", json={})
    assert resp.status_code == 422