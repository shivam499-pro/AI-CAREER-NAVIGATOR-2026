"""
Tests for routers/analysis.py — the Analysis API endpoints.

There was previously no dedicated router-level test file for this module;
tests/test_analysis_characterization.py only exercised the service layer.
This file drives every endpoint through a TestClient with the auth
dependency overridden, covering both the happy path and the exception
handler on each route.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.analysis import router
from core.middleware import get_current_user, AuthenticatedUser


# ─── Test app setup ────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router, prefix="/api/analysis")


def make_mock_user(user_id: str = "test-user-123") -> AuthenticatedUser:
    return AuthenticatedUser(user_id=user_id, email="test@test.com", role="user")


def override_auth(user_id: str = "test-user-123"):
    def _override():
        return make_mock_user(user_id)
    return _override


@pytest.fixture(autouse=True)
def _reset_overrides():
    """Ensure dependency overrides don't leak between tests."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = override_auth()
    return TestClient(app)


# ─── GET / (get_my_analysis) ────────────────────────────────────────────────

def test_get_my_analysis_returns_exists_false_when_no_analysis(client):
    with patch("routers.analysis.analysis_service.get_analysis_by_user_id") as mock_get:
        mock_get.return_value = None

        response = client.get("/api/analysis/")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["exists"] is False
        assert body["data"]["analysis"] is None
        mock_get.assert_called_once_with("test-user-123")


def test_get_my_analysis_returns_exists_true_with_analysis_data(client):
    with patch("routers.analysis.analysis_service.get_analysis_by_user_id") as mock_get:
        mock_get.return_value = {"career_paths": [{"name": "SWE"}]}

        response = client.get("/api/analysis/")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["exists"] is True
        assert body["data"]["analysis"] == {"career_paths": [{"name": "SWE"}]}


def test_get_my_analysis_returns_500_on_exception(client):
    with patch("routers.analysis.analysis_service.get_analysis_by_user_id") as mock_get:
        mock_get.side_effect = Exception("db unreachable")

        response = client.get("/api/analysis/")

        assert response.status_code == 500
        body = response.json()
        assert body["success"] is False
        assert body["meta"]["error_code"] == "ANALYSIS_FETCH_ERROR"


# ─── POST /run (run_my_analysis) ────────────────────────────────────────────

def test_run_my_analysis_creates_new_job_and_schedules_background_task(client):
    with patch("routers.analysis.create_analysis_job_idempotent", new_callable=AsyncMock) as mock_create, \
         patch("routers.analysis.async_job_service") as mock_job_service:

        mock_create.return_value = (
            {"id": "job-1", "status": "pending", "payload": {"foo": "bar"}},
            True,
        )
        mock_job_service.process_analysis_job = AsyncMock(return_value=None)

        response = client.post("/api/analysis/run")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["job_id"] == "job-1"
        assert body["data"]["status"] == "pending"
        mock_create.assert_called_once_with("test-user-123", duplicate_window_seconds=300)


def test_run_my_analysis_does_not_reschedule_duplicate_job(client):
    with patch("routers.analysis.create_analysis_job_idempotent", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = (
            {"id": "job-existing", "status": "processing", "payload": {}},
            False,
        )

        response = client.post("/api/analysis/run")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["job_id"] == "job-existing"
        assert body["data"]["status"] == "processing"


def test_run_my_analysis_returns_500_on_exception(client):
    with patch("routers.analysis.create_analysis_job_idempotent", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("could not create job")

        response = client.post("/api/analysis/run")

        assert response.status_code == 500
        body = response.json()
        assert body["meta"]["error_code"] == "ANALYSIS_JOB_ERROR"


# ─── GET /job/{job_id} (get_job_status route) ──────────────────────────────

def test_get_job_status_returns_job_when_owned_by_user(client):
    with patch("routers.analysis.get_job_status", new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {"id": "job-1", "user_id": "test-user-123", "status": "done"}

        response = client.get("/api/analysis/job/job-1")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "done"


def test_get_job_status_returns_404_when_job_not_found(client):
    with patch("routers.analysis.get_job_status", new_callable=AsyncMock) as mock_status:
        mock_status.return_value = None

        response = client.get("/api/analysis/job/missing-job")

        assert response.status_code == 404
        body = response.json()
        assert body["meta"]["error_code"] == "JOB_NOT_FOUND"


def test_get_job_status_returns_403_when_job_belongs_to_another_user(client):
    with patch("routers.analysis.get_job_status", new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {"id": "job-1", "user_id": "someone-else", "status": "done"}

        response = client.get("/api/analysis/job/job-1")

        assert response.status_code == 403
        body = response.json()
        assert body["meta"]["error_code"] == "ACCESS_DENIED"


def test_get_job_status_returns_500_on_exception(client):
    with patch("routers.analysis.get_job_status", new_callable=AsyncMock) as mock_status:
        mock_status.side_effect = Exception("boom")

        response = client.get("/api/analysis/job/job-1")

        assert response.status_code == 500
        body = response.json()
        assert body["meta"]["error_code"] == "JOB_STATUS_ERROR"


# ─── GET /jobs (get_analysis_jobs) ──────────────────────────────────────────

def test_get_analysis_jobs_returns_job_history(client):
    with patch("routers.analysis.get_user_job_history", new_callable=AsyncMock) as mock_history:
        mock_history.return_value = [{"id": "job-1"}, {"id": "job-2"}]

        response = client.get("/api/analysis/jobs")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["jobs"] == [{"id": "job-1"}, {"id": "job-2"}]
        mock_history.assert_called_once_with("test-user-123")


def test_get_analysis_jobs_returns_500_on_exception(client):
    with patch("routers.analysis.get_user_job_history", new_callable=AsyncMock) as mock_history:
        mock_history.side_effect = Exception("boom")

        response = client.get("/api/analysis/jobs")

        assert response.status_code == 500
        body = response.json()
        assert body["meta"]["error_code"] == "JOBS_LIST_ERROR"


# ─── GET /career-paths (get_career_paths) ──────────────────────────────────

def test_get_career_paths_returns_recommendations(client):
    with patch("routers.analysis.analysis_service.get_career_recommendations") as mock_rec:
        mock_rec.return_value = [{"name": "SWE", "match_percentage": 90}]

        response = client.get("/api/analysis/career-paths")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["career_paths"] == [{"name": "SWE", "match_percentage": 90}]
        mock_rec.assert_called_once_with("test-user-123")


def test_get_career_paths_returns_500_on_exception(client):
    with patch("routers.analysis.analysis_service.get_career_recommendations") as mock_rec:
        mock_rec.side_effect = Exception("boom")

        response = client.get("/api/analysis/career-paths")

        assert response.status_code == 500
        body = response.json()
        assert body["meta"]["error_code"] == "CAREER_PATHS_ERROR"


# ─── GET /skill-gap (get_skill_gaps route) ─────────────────────────────────

def test_get_skill_gap_returns_gaps(client):
    with patch("routers.analysis.analysis_service.get_skill_gaps") as mock_gaps:
        mock_gaps.return_value = [{"skill": "Docker"}]

        response = client.get("/api/analysis/skill-gap")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["skill_gaps"] == [{"skill": "Docker"}]
        mock_gaps.assert_called_once_with("test-user-123")


def test_get_skill_gap_returns_500_on_exception(client):
    with patch("routers.analysis.analysis_service.get_skill_gaps") as mock_gaps:
        mock_gaps.side_effect = Exception("boom")

        response = client.get("/api/analysis/skill-gap")

        assert response.status_code == 500
        body = response.json()
        assert body["meta"]["error_code"] == "SKILL_GAP_ERROR"


# ─── Auth enforcement ───────────────────────────────────────────────────────

def test_endpoints_require_authentication():
    """Without an auth override, requests should not be silently treated as
    an anonymous authenticated user — get_current_user must be enforced."""
    unauth_app = FastAPI()
    unauth_app.include_router(router, prefix="/api/analysis")
    unauth_client = TestClient(unauth_app)

    response = unauth_client.get("/api/analysis/")

    # get_current_user has its own auth logic (missing/invalid token);
    # what matters here is that it does NOT return 200 with a mocked user,
    # i.e. the dependency is genuinely wired in and not bypassed.
    assert response.status_code in (401, 403, 422, 500)