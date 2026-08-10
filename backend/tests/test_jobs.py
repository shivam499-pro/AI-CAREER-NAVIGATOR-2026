"""
Tests for routers/jobs.py.

Note: this router builds its own standalone supabase client via a local
get_supabase() (reading SUPABASE_URL/SUPABASE_SERVICE_KEY directly), separate
from core/supabase_client.py's centralized client — same one-off pattern as
routers/ranks.py.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.jobs import router
from core.middleware import get_current_user, AuthenticatedUser


# ─── Test App Setup ───────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router, prefix="/api/v1/jobs")


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


def empty_user_data_mock():
    """A get_supabase mock where both profiles and analyses come back empty —
    matches what get_user_data() expects to query."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    return mock_sb


# ─── 1. GET /recommendations ──────────────────────────────────────────────────

class TestGetJobRecommendations:

    def test_no_query_falls_back_to_mock_data(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", return_value=empty_user_data_mock()), \
             patch("services.job_matching_service.match_jobs") as mock_match:
            mock_match.side_effect = lambda user, jobs, limit=20: jobs  # passthrough

            response = client.get("/api/v1/jobs/recommendations")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["match_source"] == "default"  # no profile -> "default"
        assert body["count"] > 0

    def test_query_uses_serpapi_results_when_available(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", return_value=empty_user_data_mock()), \
             patch("routers.jobs.jobs_service.search_jobs", new_callable=AsyncMock) as mock_search, \
             patch("services.job_matching_service.match_jobs") as mock_match:
            mock_search.return_value = [{"id": "real_1", "title": "Real Job"}]
            mock_match.side_effect = lambda user, jobs, limit=20: jobs

            response = client.get("/api/v1/jobs/recommendations?query=python+developer")

        assert response.status_code == 200
        body = response.json()
        assert body["jobs"][0]["id"] == "real_1"

    def test_query_serpapi_empty_falls_back_to_mock(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", return_value=empty_user_data_mock()), \
             patch("routers.jobs.jobs_service.search_jobs", new_callable=AsyncMock) as mock_search, \
             patch("services.job_matching_service.match_jobs") as mock_match:
            mock_search.return_value = []  # SerpAPI returned nothing
            mock_match.side_effect = lambda user, jobs, limit=20: jobs

            response = client.get("/api/v1/jobs/recommendations?query=obscure+role")

        assert response.status_code == 200
        # Falls back to mock jobs, which always returns entries
        assert response.json()["count"] > 0

    def test_serpapi_misconfigured_returns_503(self):
        """ValueError (missing SERPAPI_KEY) must map to 503, not be swallowed
        into a generic 500 by the outer handler."""
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", return_value=empty_user_data_mock()), \
             patch("routers.jobs.jobs_service.search_jobs", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = ValueError("SERPAPI_KEY is not configured.")

            response = client.get("/api/v1/jobs/recommendations?query=python")

        assert response.status_code == 503

    def test_serpapi_upstream_failure_returns_502(self):
        """A generic (non-ValueError) failure from search_jobs — e.g. the
        actual SerpAPI call failing — must map to 502, not 500."""
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", return_value=empty_user_data_mock()), \
             patch("routers.jobs.jobs_service.search_jobs", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = RuntimeError("SerpAPI request timed out")

            response = client.get("/api/v1/jobs/recommendations?query=python")

        assert response.status_code == 502
        assert "Job search unavailable" in response.json()["detail"]

    def test_profile_present_sets_match_source_ai_matching(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"user_id": "test-user-123", "skills": ["Python"]}
        ]

        with patch("routers.jobs.get_supabase", return_value=mock_sb), \
             patch("services.job_matching_service.match_jobs") as mock_match:
            mock_match.side_effect = lambda user, jobs, limit=20: jobs

            response = client.get("/api/v1/jobs/recommendations")

        assert response.status_code == 200
        assert response.json()["match_source"] == "ai_matching"

    def test_pagination_slices_results_correctly(self):
        app.dependency_overrides[get_current_user] = override_auth()

        fake_jobs = [{"id": f"job_{i}"} for i in range(25)]

        with patch("routers.jobs.get_supabase", return_value=empty_user_data_mock()), \
             patch("services.job_matching_service.match_jobs") as mock_match:
            mock_match.return_value = fake_jobs

            response = client.get("/api/v1/jobs/recommendations?page=2&limit=10")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 10
        assert body["jobs"][0]["id"] == "job_10"
        assert body["pagination"]["total_pages"] == 3

    def test_unexpected_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", side_effect=Exception("total outage")):
            response = client.get("/api/v1/jobs/recommendations")

        assert response.status_code == 500


# ─── 2. GET /applications ─────────────────────────────────────────────────────

class TestGetApplications:

    def test_counts_by_status(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"status": "applied"}, {"status": "applied"},
            {"status": "interview"}, {"status": "offer"}, {"status": "rejected"},
        ]

        with patch("routers.jobs.get_supabase", return_value=mock_sb):
            response = client.get("/api/v1/jobs/applications")

        assert response.status_code == 200
        body = response.json()
        assert body["status_counts"] == {"applied": 2, "interview": 1, "rejected": 1, "offer": 1}
        assert body["total"] == 5

    def test_unknown_status_falls_back_to_applied_bucket(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"status": "ghosted"},  # not a recognized bucket
        ]

        with patch("routers.jobs.get_supabase", return_value=mock_sb):
            response = client.get("/api/v1/jobs/applications")

        assert response.status_code == 200
        assert response.json()["status_counts"]["applied"] == 1

    def test_no_applications_returns_zero_counts(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", return_value=empty_user_data_mock()):
            response = client.get("/api/v1/jobs/applications")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert all(v == 0 for v in body["status_counts"].values())

    def test_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", side_effect=Exception("boom")):
            response = client.get("/api/v1/jobs/applications")

        assert response.status_code == 500


# ─── 3. POST /save ────────────────────────────────────────────────────────────

class TestSaveJob:

    SAVE_BODY = {
        "job_id": "job_1", "title": "Backend Engineer", "company": "Acme",
        "location": "Remote", "apply_url": "https://example.com/apply",
        "match_score": 0.9, "matched_skills": ["Python"], "missing_skills": []
    }

    def test_save_new_job(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        with patch("routers.jobs.get_supabase", return_value=mock_sb):
            response = client.post("/api/v1/jobs/save", json=self.SAVE_BODY)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["already_saved"] is False
        mock_sb.table.return_value.insert.assert_called_once()

    def test_save_job_already_saved_is_idempotent(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1}
        ]

        with patch("routers.jobs.get_supabase", return_value=mock_sb):
            response = client.post("/api/v1/jobs/save", json=self.SAVE_BODY)

        assert response.status_code == 200
        body = response.json()
        assert body["already_saved"] is True
        mock_sb.table.return_value.insert.assert_not_called()

    def test_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", side_effect=Exception("boom")):
            response = client.post("/api/v1/jobs/save", json=self.SAVE_BODY)

        assert response.status_code == 500


# ─── 4. POST /apply ───────────────────────────────────────────────────────────

class TestApplyToJob:

    APPLY_BODY = {
        "job_id": "job_1", "title": "Backend Engineer", "company": "Acme",
        "location": "Remote", "apply_url": "https://example.com/apply",
        "match_score": 0.9, "matched_skills": ["Python"], "missing_skills": []
    }

    def test_apply_new_job(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        with patch("routers.jobs.get_supabase", return_value=mock_sb):
            response = client.post("/api/v1/jobs/apply", json=self.APPLY_BODY)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["duplicate"] is False
        insert_call = mock_sb.table.return_value.insert.call_args.args[0]
        assert insert_call["status"] == "applied"

    def test_apply_duplicate_application(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1}
        ]

        with patch("routers.jobs.get_supabase", return_value=mock_sb):
            response = client.post("/api/v1/jobs/apply", json=self.APPLY_BODY)

        assert response.status_code == 200
        body = response.json()
        assert body["duplicate"] is True
        mock_sb.table.return_value.insert.assert_not_called()

    def test_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.jobs.get_supabase", side_effect=Exception("boom")):
            response = client.post("/api/v1/jobs/apply", json=self.APPLY_BODY)

        assert response.status_code == 500


# ─── 5. _mock_jobs() filtering logic ──────────────────────────────────────────

class TestMockJobsFallback:

    def test_filters_by_location(self):
        from routers.jobs import _mock_jobs
        results = _mock_jobs(query=None, location="Chennai", job_type=None)
        assert len(results) >= 1
        assert all("chennai" in j["location"].lower() for j in results)

    def test_filters_by_job_type(self):
        from routers.jobs import _mock_jobs
        results = _mock_jobs(query=None, location=None, job_type="Internship")
        assert len(results) >= 1
        assert all("internship" in j["type"].lower() for j in results)

    def test_query_customizes_job_titles(self):
        from routers.jobs import _mock_jobs
        results = _mock_jobs(query="Data Scientist", location=None, job_type=None)
        assert any("Data Scientist" in j["title"] for j in results)


class TestGetSupabaseHelper:
    def test_get_supabase_creates_client_with_env_vars(self, monkeypatch):
        """Happy path: both env vars set -> create_client(url, key)."""
        monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-service-key")

        from routers.jobs import get_supabase

        with patch("routers.jobs.create_client") as mock_create_client:
            mock_create_client.return_value = MagicMock()
            result = get_supabase()

        mock_create_client.assert_called_once_with(
            "https://fake.supabase.co", "fake-service-key"
        )
        assert result is mock_create_client.return_value

    def test_get_supabase_raises_when_env_vars_missing(self, monkeypatch):
        """Missing SUPABASE_URL or SUPABASE_SERVICE_KEY -> ValueError."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")

        from routers.jobs import get_supabase

        with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"):
            get_supabase()