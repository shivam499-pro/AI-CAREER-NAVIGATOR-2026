"""
Tests for routers/profile.py

profile_service functions are mocked at the boundary — they already have
dedicated coverage in tests/test_profile_service.py. These tests exist to
verify the ROUTER's job specifically: auth wiring, request->service
orchestration, response envelope shaping, and error->500 mapping. That's
the actual 62%->100% gap; re-testing profile_service internals here would
just be duplicate coverage with no new signal.

core.middleware and lib.auth are stubbed for import purposes only (see
core/middleware.py, lib/auth.py in this sandbox) — real implementations
live in batch 1. APIResponse is patched per-test with a stub matching how
this router actually calls it (data=..., message=...).

Design note carried from review: `get_match_fit`'s target_goal matching
uses plain substring containment (`target_goal.lower() in name.lower()`),
not word-boundary matching. test_match_fit_substring_matching_is_naive
documents this as a real bug, not intended behavior.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import profile as profile_module
from routers.profile import router, get_current_user


class _StubAPIResponse:
    @staticmethod
    def success_response(data=None, message=None):
        return {"success": True, "data": data, "message": message}

    @staticmethod
    def error_response(message, code=None):
        return {"success": False, "error": message, "code": code}


class _StubUser:
    def __init__(self, user_id="user-A"):
        self.user_id = user_id


app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def _patch_api_response():
    with patch.object(profile_module, "APIResponse", _StubAPIResponse):
        yield


@pytest.fixture
def auth_as():
    def _set(user_id="user-A"):
        app.dependency_overrides[get_current_user] = lambda: _StubUser(user_id)
    yield _set
    app.dependency_overrides.clear()


# ─── GET /me ───────────────────────────────────────────────────────────────────

def test_get_my_profile_returns_enriched_profile(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_enriched_profile") as mock_get:
        mock_get.return_value = {"exists": True, "user_id": "user-A", "completeness": 80}
        resp = client.get("/me")

    assert resp.status_code == 200
    assert resp.json()["data"]["profile"]["completeness"] == 80
    mock_get.assert_called_once_with("user-A")


def test_get_my_profile_service_error_returns_500(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_enriched_profile") as mock_get:
        mock_get.side_effect = Exception("supabase down")
        resp = client.get("/me")

    assert resp.status_code == 500
    assert resp.json()["code"] == "PROFILE_FETCH_ERROR"


def test_get_my_profile_is_scoped_to_the_authenticated_user_only(auth_as):
    # Confirms the router never trusts a client-supplied user id — it always
    # uses the id from the verified token.
    auth_as("user-Z")
    with patch.object(profile_module.profile_service, "get_enriched_profile") as mock_get:
        mock_get.return_value = {"exists": True}
        client.get("/me")

    mock_get.assert_called_once_with("user-Z")


# ─── POST /save ────────────────────────────────────────────────────────────────

def test_save_my_profile_success(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "save_profile") as mock_save:
        mock_save.return_value = True
        resp = client.post("/save", json={"college_name": "REC", "graduation_year": 2028})

    assert resp.status_code == 200
    assert resp.json()["data"]["saved"] is True
    args, _ = mock_save.call_args
    assert args[0] == "user-A"
    # Note: exclude_none removes unset Optional fields, but the four
    # List fields default to [] (not None), so they always survive and
    # reach the service even when the caller sent nothing for them.
    assert args[1] == {
        "college_name": "REC",
        "graduation_year": 2028,
        "current_tech_stack": [],
        "extra_skills": [],
        "certificates": [],
        "target_companies": [],
    }


def test_save_my_profile_excludes_none_fields_from_payload(auth_as):
    # ProfileSaveRequest has ~25 Optional fields; only fields actually sent
    # should reach the service, not the whole model dumped with None noise.
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "save_profile") as mock_save:
        mock_save.return_value = True
        client.post("/save", json={"career_goal": "AI Engineer"})

    args, _ = mock_save.call_args
    saved_data = args[1]
    assert saved_data == {
        "career_goal": "AI Engineer",
        "current_tech_stack": [],
        "extra_skills": [],
        "certificates": [],
        "target_companies": [],
    }
    # explicitly confirm untouched optional fields did not leak through
    assert "college_name" not in saved_data
    assert "cgpa" not in saved_data


def test_save_my_profile_service_returns_false_yields_500(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "save_profile") as mock_save:
        mock_save.return_value = False
        resp = client.post("/save", json={"career_goal": "AI Engineer"})

    assert resp.status_code == 500
    assert resp.json()["code"] == "PROFILE_SAVE_ERROR"


def test_save_my_profile_service_exception_yields_500(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "save_profile") as mock_save:
        mock_save.side_effect = Exception("write conflict")
        resp = client.post("/save", json={"career_goal": "AI Engineer"})

    assert resp.status_code == 500
    assert resp.json()["code"] == "PROFILE_SAVE_ERROR"


def test_save_my_profile_reraises_http_exception_from_service(auth_as):
    # Covers the `except HTTPException: raise` branch. Currently nothing in
    # profile_service raises HTTPException, so this branch is effectively
    # dead under present usage — but it's defensive code for a future
    # service that does raise one (e.g. a 403 from a permission check), and
    # it needs to bypass the generic 500 wrapper below it, not get caught
    # by it. Confirming that ordering holds.
    from fastapi import HTTPException
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "save_profile") as mock_save:
        mock_save.side_effect = HTTPException(status_code=403, detail="Forbidden by policy")
        resp = client.post("/save", json={"career_goal": "AI Engineer"})

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Forbidden by policy"
    # graduation_year is Optional[int] — a non-numeric string should 422
    # before ever reaching the service layer.
    auth_as("user-A")
    resp = client.post("/save", json={"graduation_year": "not-a-year"})
    assert resp.status_code == 422


# ─── GET /progress ─────────────────────────────────────────────────────────────

def test_get_my_progress_success(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_user_progress") as mock_progress:
        mock_progress.return_value = {"steps": [], "total_percent": 40}
        resp = client.get("/progress")

    assert resp.status_code == 200
    assert resp.json()["data"]["progress"]["total_percent"] == 40


def test_get_my_progress_service_error_returns_500(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_user_progress") as mock_progress:
        mock_progress.side_effect = Exception("timeout")
        resp = client.get("/progress")

    assert resp.status_code == 500
    assert resp.json()["code"] == "PROGRESS_FETCH_ERROR"


# ─── GET /match-fit ─────────────────────────────────────────────────────────────

def test_match_fit_no_analysis_returns_optimization_required_default(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_profile_by_user_id") as mock_profile, \
         patch("services.analysis_service.get_analysis_by_user_id") as mock_analysis:
        mock_profile.return_value = {"career_goal": "AI Engineer"}
        mock_analysis.return_value = None

        resp = client.get("/match-fit")

    body = resp.json()["data"]
    assert body["score"] == 0
    assert body["label"] == "Optimization Required"
    assert body["role"] == "AI Engineer"


def test_match_fit_no_profile_and_no_analysis_role_is_unspecified(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_profile_by_user_id") as mock_profile, \
         patch("services.analysis_service.get_analysis_by_user_id") as mock_analysis:
        mock_profile.return_value = None
        mock_analysis.return_value = None

        resp = client.get("/match-fit")

    assert resp.json()["data"]["role"] == "Unspecified"


def test_match_fit_finds_matching_career_path_by_target_goal(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_profile_by_user_id") as mock_profile, \
         patch("services.analysis_service.get_analysis_by_user_id") as mock_analysis:
        mock_profile.return_value = {"career_goal": "Backend Engineer"}
        mock_analysis.return_value = {
            "career_paths": [
                {"name": "Frontend Engineer", "match_percentage": 60},
                {"name": "Backend Engineer", "match_percentage": 92, "reason": "Strong fit"},
            ]
        }

        resp = client.get("/match-fit")

    body = resp.json()["data"]
    assert body["role"] == "Backend Engineer"
    assert body["score"] == 92
    assert body["label"] == "ELITE ALIGNMENT"
    assert body["reason"] == "Strong fit"


def test_match_fit_falls_back_to_first_path_when_no_target_goal_match(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_profile_by_user_id") as mock_profile, \
         patch("services.analysis_service.get_analysis_by_user_id") as mock_analysis:
        mock_profile.return_value = {"career_goal": "Quantum Computing Specialist"}
        mock_analysis.return_value = {
            "career_paths": [{"name": "Backend Engineer", "match_percentage": 55}]
        }

        resp = client.get("/match-fit")

    body = resp.json()["data"]
    assert body["role"] == "Backend Engineer"
    assert body["label"] == "STRATEGIC MATCH"


@pytest.mark.parametrize("score,expected_label", [
    (95, "ELITE ALIGNMENT"),
    (90, "ELITE ALIGNMENT"),
    (89, "HIGHLY COMPATIBLE"),
    (75, "HIGHLY COMPATIBLE"),
    (74, "STRATEGIC MATCH"),
    (50, "STRATEGIC MATCH"),
    (49, "EMERGING SYNC"),
    (0, "EMERGING SYNC"),
])
def test_match_fit_label_thresholds(auth_as, score, expected_label):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_profile_by_user_id") as mock_profile, \
         patch("services.analysis_service.get_analysis_by_user_id") as mock_analysis:
        mock_profile.return_value = {"career_goal": "X"}
        mock_analysis.return_value = {
            "career_paths": [{"name": "X", "match_percentage": score}]
        }
        resp = client.get("/match-fit")

    assert resp.json()["data"]["label"] == expected_label


def test_match_fit_substring_matching_is_naive():
    # BUG (see review): target_goal matching is plain substring containment,
    # not word-boundary matching. A short/generic target_goal can spuriously
    # match an unrelated career path name that merely contains those
    # characters in sequence. This documents CURRENT behavior — not a
    # recommendation to keep it this way.
    app.dependency_overrides[get_current_user] = lambda: _StubUser("user-A")
    try:
        with patch.object(profile_module.profile_service, "get_profile_by_user_id") as mock_profile, \
             patch("services.analysis_service.get_analysis_by_user_id") as mock_analysis:
            mock_profile.return_value = {"career_goal": "ai"}
            mock_analysis.return_value = {
                "career_paths": [
                    {"name": "Retail Manager", "match_percentage": 40},   # contains "ai" (in "ret-ai-l")... 
                    {"name": "Backend Engineer", "match_percentage": 90},
                ]
            }
            resp = client.get("/match-fit")

        # "Retail Manager" contains "ai" as a substring ("ret-AI-l") and comes
        # first in the list, so it wins the match despite being unrelated to
        # an "ai" career goal — the intended target was almost certainly
        # "AI Engineer"-type roles, not a false-positive substring hit.
        assert resp.json()["data"]["role"] == "Retail Manager"
    finally:
        app.dependency_overrides.clear()


def test_match_fit_service_exception_returns_500(auth_as):
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_profile_by_user_id") as mock_profile:
        mock_profile.side_effect = Exception("db error")
        resp = client.get("/match-fit")

    assert resp.status_code == 500
    assert resp.json()["code"] == "MATCH_FIT_ERROR"

def test_match_fit_falls_through_to_no_data_when_first_path_is_empty_dict(auth_as):
    """career_paths is non-empty (passes the early-return guard) but its
    first element is a falsy empty dict -- the fallback assignment still
    'succeeds' (finds an item) yet leaves match_path falsy, landing on the
    final 'No Data' branch rather than crashing."""
    auth_as("user-A")
    with patch.object(profile_module.profile_service, "get_profile_by_user_id") as mock_profile, \
         patch("services.analysis_service.get_analysis_by_user_id") as mock_analysis:
        mock_profile.return_value = None
        mock_analysis.return_value = {"career_paths": [{}]}

        resp = client.get("/match-fit")

    body = resp.json()["data"]
    assert body["score"] == 0
    assert body["label"] == "No Data"
    assert body["role"] == "Pending"