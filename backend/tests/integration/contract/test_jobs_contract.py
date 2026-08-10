"""
Jobs Contract Tests
jobsClient.ts expects exact response shapes for job recommendations,
saved jobs, and applications.

IMPORTANT: routers/jobs.py does NOT use the shared core.supabase_client
singleton (nor the mock_supabase fixture that patches it) -- it defines
its own local get_supabase() -> create_client(url, key), the same one-off
pattern as routers/documents.py and routers/resume.py. The root
tests/conftest.py's global supabase.create_client patch is also disabled
(commented out). So every test here patches routers.jobs.create_client
directly instead of using the mock_supabase fixture.

This is also the highest cross-component-risk router in the app: it's
the only place get_user_data()'s real output (profile + analysis +
experience_level) gets fed into the REAL job_matching_service.match_jobs()
-- a boundary unit tests can't see, since they mock one side or the
other separately.
"""
import pytest
from unittest.mock import patch, MagicMock
from tests.integration.conftest import TEST_USER_ID, make_supabase_response


def _mock_jobs_client():
    """A fresh MagicMock standing in for create_client()'s return value."""
    return MagicMock()


@pytest.mark.integration
class TestJobsContract:

    def test_recommendations_real_matching_scores_job_against_real_profile(self, authed_client):
        """
        The one place get_user_data()'s real output shape actually meets
        job_matching_service.match_jobs()'s real expected input shape.
        Neither side is mocked here -- only the Supabase layer is -- so
        this is the only test that would catch a shape mismatch between
        the two (e.g. if either side changed its key names independently).
        """
        mock_client = _mock_jobs_client()
        profile_response = make_supabase_response([{
            "user_id": TEST_USER_ID,
            "extra_skills": ["Python", "FastAPI", "PostgreSQL"],
            "career_goal": "Backend Engineer"
        }])
        analysis_response = make_supabase_response([{
            "experience_level": "mid",
            "skill_gaps": ["Docker", "Kubernetes"]
        }])
        mock_client.table.return_value.select.return_value.eq.return_value \
            .execute.side_effect = [profile_response, analysis_response]

        with patch("routers.jobs.create_client", return_value=mock_client):
            response = authed_client.get("/api/v1/jobs/recommendations")

        assert response.status_code == 200
        body = response.json()
        assert body["match_source"] == "ai_matching"
        assert len(body["jobs"]) > 0

        top_job = body["jobs"][0]  # match_jobs() sorts descending by score
        assert top_job["company"] == "Tech Corp"  # the Python/FastAPI/PostgreSQL listing
        assert top_job["match_score"] > 0
        assert "python" in [s.lower() for s in top_job["matched_skills"]]

    def test_recommendations_no_profile_uses_default_match_source(self, authed_client):
        """No profile/analysis at all -- still returns mock jobs, but
        match_source must say 'default' so the frontend doesn't claim
        AI-personalized results it didn't actually produce."""
        mock_client = _mock_jobs_client()
        mock_client.table.return_value.select.return_value.eq.return_value \
            .execute.return_value = make_supabase_response([])

        with patch("routers.jobs.create_client", return_value=mock_client):
            response = authed_client.get("/api/v1/jobs/recommendations")

        assert response.status_code == 200
        body = response.json()
        assert body["match_source"] == "default"
        assert len(body["jobs"]) > 0

    def test_recommendations_search_value_error_returns_503(self, authed_client):
        """jobs_service.search_jobs raising ValueError (e.g. missing
        SERPAPI_KEY) must surface as 503, not a generic 500 -- frontend
        shows a specific 'search unavailable' message on 503."""
        mock_client = _mock_jobs_client()
        mock_client.table.return_value.select.return_value.eq.return_value \
            .execute.return_value = make_supabase_response([])

        with patch("routers.jobs.create_client", return_value=mock_client), \
             patch("routers.jobs.jobs_service.search_jobs") as mock_search:
            mock_search.side_effect = ValueError("SERPAPI_KEY not configured")
            response = authed_client.get("/api/v1/jobs/recommendations?query=backend+engineer")

        assert response.status_code == 503

    def test_recommendations_search_generic_exception_returns_502(self, authed_client):
        """A genuine SerpAPI failure (network, quota, etc.) must surface
        as 502, distinct from the 503 config-missing case above."""
        mock_client = _mock_jobs_client()
        mock_client.table.return_value.select.return_value.eq.return_value \
            .execute.return_value = make_supabase_response([])

        with patch("routers.jobs.create_client", return_value=mock_client), \
             patch("routers.jobs.jobs_service.search_jobs") as mock_search:
            mock_search.side_effect = Exception("SerpAPI timeout")
            response = authed_client.get("/api/v1/jobs/recommendations?query=backend+engineer")

        assert response.status_code == 502

    def test_applications_buckets_unknown_status_as_applied(self, authed_client):
        """dashboardPipeline.tsx sums status_counts -- an unrecognized
        status value must not silently vanish from the total."""
        mock_client = _mock_jobs_client()
        mock_client.table.return_value.select.return_value.eq.return_value \
            .execute.return_value = make_supabase_response([
                {"status": "applied"},
                {"status": "interview"},
                {"status": "some_weird_new_status"},
            ])

        with patch("routers.jobs.create_client", return_value=mock_client):
            response = authed_client.get("/api/v1/jobs/applications")

        assert response.status_code == 200
        body = response.json()
        assert body["status_counts"]["applied"] == 2  # 1 real + 1 unknown bucketed in
        assert body["status_counts"]["interview"] == 1
        assert body["total"] == 3

    def test_save_job_is_idempotent_on_second_save(self, authed_client):
        """savedJobsClient.ts calls save() without checking first --
        the backend must be the one enforcing no-duplicate-insert."""
        mock_client = _mock_jobs_client()
        mock_client.table.return_value.select.return_value.eq.return_value \
            .eq.return_value.execute.return_value = \
            make_supabase_response([{"id": "existing-save-1"}])

        payload = {"job_id": "job-1", "title": "Backend Engineer", "company": "Acme"}

        with patch("routers.jobs.create_client", return_value=mock_client):
            response = authed_client.post("/api/v1/jobs/save", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["already_saved"] is True
        mock_client.table.return_value.insert.assert_not_called()

    def test_apply_to_job_is_idempotent_on_second_apply(self, authed_client):
        """Same idempotency contract as /save, for job_applications --
        a duplicate apply must not create a second row or reset status."""
        mock_client = _mock_jobs_client()
        mock_client.table.return_value.select.return_value.eq.return_value \
            .eq.return_value.execute.return_value = \
            make_supabase_response([{"id": "existing-application-1"}])

        payload = {
            "job_id": "job-1", "title": "Backend Engineer", "company": "Acme",
            "apply_url": "https://example.com/apply"
        }

        with patch("routers.jobs.create_client", return_value=mock_client):
            response = authed_client.post("/api/v1/jobs/apply", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["duplicate"] is True
        assert body["apply_url"] == "https://example.com/apply"
        mock_client.table.return_value.insert.assert_not_called()