"""
Tests for routers/roadmap.py

core.middleware (AuthenticatedUser, get_current_user, APIResponse) and
core.supabase_client (get_supabase) are NOT part of this batch — they're
shared infra from elsewhere in the app. Rather than guess their internals,
these tests patch at the boundary:
  - `routers.roadmap.get_supabase` is replaced with a configurable fake
  - `routers.roadmap.APIResponse` is replaced with a minimal stub whose
    contract (success_response/error_response return a dict we can assert on)
    matches how the router calls it — this decouples these tests from an
    implementation we can't see, while still verifying roadmap.py's own logic.
  - auth is satisfied via FastAPI's dependency_overrides on get_current_user,
    same pattern already used in test_badges.py.

Known design debt this file's tests intentionally do NOT try to work around
(see review notes): the cooldown rule and completion-aggregation logic live
inline in the router instead of a service layer. These tests pin down
CURRENT behavior so that extraction can happen safely later.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import roadmap as roadmap_module
from routers.roadmap import router


# ─── Stubs for external contracts not present in this batch ──────────────────

class _StubAPIResponse:
    @staticmethod
    def success_response(data=None):
        return {"success": True, "data": data}

    @staticmethod
    def error_response(message, code=None):
        return {"success": False, "error": message, "code": code}


class _StubAuthenticatedUser:
    def __init__(self, user_id):
        self.user_id = user_id


def _fake_get_current_user(user_id="user-A"):
    def _dep():
        return _StubAuthenticatedUser(user_id)
    return _dep


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _make_supabase_mock(execute_results):
    """
    Build a MagicMock chain where every builder method (.table/.select/.eq/
    .order/.limit/.upsert) returns the same chainable mock, and successive
    .execute() calls return the given results in order — mirroring that
    each endpoint may issue multiple independent queries per request.
    """
    chain = MagicMock()
    for method in ("table", "select", "eq", "order", "limit", "upsert"):
        getattr(chain, method).return_value = chain
    chain.execute.side_effect = execute_results
    supabase = MagicMock()
    supabase.table.return_value = chain
    return supabase, chain


def _qres(data):
    r = MagicMock()
    r.data = data
    return r


@pytest.fixture(autouse=True)
def _patch_api_response():
    with patch.object(roadmap_module, "APIResponse", _StubAPIResponse):
        yield


@pytest.fixture
def auth_as():
    def _set(user_id="user-A"):
        app.dependency_overrides[roadmap_module.get_current_user] = _fake_get_current_user(user_id)
    yield _set
    app.dependency_overrides.clear()


# ─── PATCH /milestone — cooldown gate ─────────────────────────────────────────

def test_completing_milestone_within_3_days_of_last_completion_is_blocked(auth_as):
    auth_as("user-A")
    recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    supabase, chain = _make_supabase_mock([_qres([{"completed_at": recent}])])

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.patch("/milestone", json={
            "career_path": "AI/ML Engineer",
            "milestone_week": 2,
            "status": "completed",
        })

    assert resp.status_code == 429
    assert resp.json()["code"] == "TOO_SOON"
    # Only the cooldown-check query should have run — upsert must NOT fire.
    assert chain.execute.call_count == 1


def test_completing_milestone_exactly_at_3_day_boundary_is_allowed(auth_as):
    auth_as("user-A")
    exactly_3_days = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat().replace("+00:00", "Z")
    supabase, chain = _make_supabase_mock([
        _qres([{"completed_at": exactly_3_days}]),   # cooldown check
        _qres(None),                                  # upsert result
        _qres([{"status": "completed"}]),              # all_progress fetch
    ])

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.patch("/milestone", json={
            "career_path": "AI/ML Engineer",
            "milestone_week": 2,
            "status": "completed",
        })

    assert resp.status_code == 200
    assert resp.json()["data"]["updated"] is True


def test_completing_milestone_with_no_prior_completions_skips_cooldown(auth_as):
    auth_as("user-A")
    supabase, chain = _make_supabase_mock([
        _qres([]),                                     # no prior completed rows
        _qres(None),                                    # upsert
        _qres([{"status": "completed"}]),                 # all_progress
    ])

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.patch("/milestone", json={
            "career_path": "Backend Engineer",
            "milestone_week": 1,
            "status": "completed",
        })

    assert resp.status_code == 200


def test_marking_in_progress_never_triggers_cooldown_check(auth_as):
    # status != "completed" must skip the cooldown branch entirely — only
    # the upsert + aggregation queries should run.
    auth_as("user-A")
    supabase, chain = _make_supabase_mock([
        _qres(None),                                    # upsert
        _qres([{"status": "in_progress"}]),               # all_progress
    ])

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.patch("/milestone", json={
            "career_path": "Backend Engineer",
            "milestone_week": 1,
            "status": "in_progress",
        })

    assert resp.status_code == 200
    assert chain.execute.call_count == 2


# ─── PATCH /milestone — completion aggregation correctness ───────────────────

def test_roadmap_completed_true_when_all_milestones_completed(auth_as):
    auth_as("user-A")
    supabase, chain = _make_supabase_mock([
        _qres([]),                                     # cooldown: no priors
        _qres(None),                                    # upsert
        _qres([{"status": "completed"}, {"status": "completed"}]),  # all done
    ])

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.patch("/milestone", json={
            "career_path": "Backend Engineer",
            "milestone_week": 2,
            "status": "completed",
        })

    body = resp.json()["data"]
    assert body["completed_count"] == 2
    assert body["total_count"] == 2
    assert body["roadmap_completed"] is True


def test_roadmap_completed_false_when_partially_completed(auth_as):
    auth_as("user-A")
    supabase, chain = _make_supabase_mock([
        _qres([]),
        _qres(None),
        _qres([{"status": "completed"}, {"status": "in_progress"}, {"status": "pending"}]),
    ])

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.patch("/milestone", json={
            "career_path": "Backend Engineer",
            "milestone_week": 2,
            "status": "completed",
        })

    body = resp.json()["data"]
    assert body["completed_count"] == 1
    assert body["total_count"] == 3
    assert body["roadmap_completed"] is False


def test_roadmap_completed_false_when_no_rows_tracked_yet():
    # Guards the `total > 0 and completed == total` check — without the
    # `total > 0` guard, an empty roadmap (0 == 0) would incorrectly read
    # as "completed".
    app.dependency_overrides[roadmap_module.get_current_user] = _fake_get_current_user("user-A")
    try:
        supabase, chain = _make_supabase_mock([
            _qres([]),
            _qres(None),
            _qres([]),  # no rows at all
        ])
        with patch.object(roadmap_module, "get_supabase", return_value=supabase):
            resp = client.patch("/milestone", json={
                "career_path": "Backend Engineer",
                "milestone_week": 1,
                "status": "completed",
            })
        body = resp.json()["data"]
        assert body["total_count"] == 0
        assert body["roadmap_completed"] is False
    finally:
        app.dependency_overrides.clear()


# ─── PATCH /milestone — error handling ────────────────────────────────────────

def test_supabase_error_during_update_returns_500_with_error_code(auth_as):
    auth_as("user-A")
    supabase = MagicMock()
    supabase.table.side_effect = Exception("connection reset")

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.patch("/milestone", json={
            "career_path": "Backend Engineer",
            "milestone_week": 1,
            "status": "pending",
        })

    assert resp.status_code == 500
    assert resp.json()["code"] == "MILESTONE_UPDATE_ERROR"


# ─── GET /progress/{career_path} ──────────────────────────────────────────────

def test_get_progress_builds_correct_map_and_counts(auth_as):
    auth_as("user-A")
    supabase, chain = _make_supabase_mock([
        _qres([
            {"milestone_week": 1, "status": "completed"},
            {"milestone_week": 2, "status": "in_progress"},
            {"milestone_week": 3, "status": "pending"},
        ]),
    ])

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.get("/progress/AI%2FML Engineer")

    body = resp.json()["data"]
    assert body["completed_count"] == 1
    assert body["in_progress_count"] == 1
    assert body["total_tracked"] == 3
    # JSON object keys are always strings on the wire, even though the
    # handler builds progress_map with int keys (`r["milestone_week"]`).
    # Frontend consumers must treat these as string keys.
    assert body["progress_map"] == {"1": "completed", "2": "in_progress", "3": "pending"}


def test_get_progress_with_no_data_returns_zeroed_empty_response(auth_as):
    auth_as("user-A")
    supabase, chain = _make_supabase_mock([_qres(None)])

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.get("/progress/Data Scientist")

    body = resp.json()["data"]
    assert body["completed_count"] == 0
    assert body["in_progress_count"] == 0
    assert body["total_tracked"] == 0
    assert body["progress_map"] == {}


def test_get_progress_supabase_error_returns_500(auth_as):
    auth_as("user-A")
    supabase = MagicMock()
    supabase.table.side_effect = Exception("timeout")

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        resp = client.get("/progress/Data Scientist")

    assert resp.status_code == 500
    assert resp.json()["code"] == "PROGRESS_FETCH_ERROR"


def test_get_progress_scoped_to_requesting_user_only(auth_as):
    # There's no cross-user ownership check here because career_path — not
    # user_id — is the path param; user scoping happens entirely via the
    # injected `user.user_id` in the query filter. This test locks in that
    # the filter is actually applied with the authenticated user's id.
    auth_as("user-Z")
    supabase, chain = _make_supabase_mock([_qres([])])

    with patch.object(roadmap_module, "get_supabase", return_value=supabase):
        client.get("/progress/Backend Engineer")

    chain.eq.assert_any_call("user_id", "user-Z")