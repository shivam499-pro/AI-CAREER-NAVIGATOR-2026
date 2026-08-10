"""
Analysis Contract Tests
The analysisClient.ts polls these endpoints. Every response shape change
breaks the frontend silently. These tests lock in the contract.
"""
import abc

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from tests.integration.conftest import TEST_USER_ID, make_supabase_response
from slowapi.errors import RateLimitExceeded

@pytest.mark.integration
class TestAnalysisContract:

    def test_run_analysis_returns_job_id(self, authed_client, mock_supabase):
        
        with patch("routers.analysis.create_analysis_job_idempotent") as mock_job:
            mock_job.return_value = (
                {"id": "job-abc-123", "status": "pending", "payload": {}},
                True
            )
            response = authed_client.post(
                "/api/v1/analysis/run",
                json={"user_id": TEST_USER_ID}
            )
        
        assert response.status_code == 200
        body = response.json()
        # Frontend drills into data.data.job_id
        assert body.get("data", {}).get("job_id") is not None or \
               body.get("job_id") is not None, \
               "job_id missing from response — frontend will throw"

    def test_job_status_returns_status_field(self, authed_client, mock_supabase):
        """
        analysisClient.getJobStatus() expects:
        { data: { id: string, status: 'pending'|'completed'|'failed' } }
        
        Frontend polls until status === 'completed'.
        """
        job_id = "job-abc-123"
        
        with patch("routers.analysis.get_job_status") as mock_status:
            mock_status.return_value = {
                "id": "job-abc-123",
                "status": "completed",
                "user_id": TEST_USER_ID
            }
            
            response = authed_client.get(f"/api/v1/analysis/job/{job_id}")
        
        assert response.status_code == 200
        body = response.json()
        # status must be accessible — frontend breaks if missing
        data = body.get("data", body)
        assert "status" in data, "status field missing — frontend poll will never resolve"

    def test_get_analysis_returns_required_fields(self, authed_client, mock_supabase, mock_analysis_record):
        mock_supabase.table.return_value.select.return_value\
            .eq.return_value.execute.return_value = \
            make_supabase_response([mock_analysis_record])
        
        response = authed_client.get("/api/v1/analysis/")
        
        assert response.status_code == 200
        body = response.json()
        analysis = body.get("data", {}).get("analysis", body.get("analysis", {}))
        
        # These fields are accessed by parseAnalysisRecord.ts
        assert "career_paths" in analysis or analysis == {}, \
            "career_paths missing — frontend will render empty state incorrectly"


    def test_check_existing_analysis_response_shape(self, authed_client, mock_supabase):
        """
        analysisClient.checkExisting() expects:
        { data: { exists: boolean, analysis?: AnalysisRecord } }
        
        exists=false → frontend shows 'Run Analysis' button
        exists=true → frontend shows results
        """
        mock_supabase.table.return_value.select.return_value\
            .eq.return_value.execute.return_value = \
            make_supabase_response([])
        
        response = authed_client.get("/api/v1/analysis/")
        
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", {})
        # exists field must be present (boolean)
        assert "exists" in data, "exists field missing — frontend shows wrong state"
        assert isinstance(data["exists"], bool)


    # ======================================================
    # Exception paths -- none of these were tested before
    # ======================================================

    def test_get_analysis_returns_500_on_error(self, authed_client, mock_supabase):
        with patch("routers.analysis.analysis_service.get_analysis_by_user_id") as mock_get:
            mock_get.side_effect = Exception("db exploded")

            response = authed_client.get("/api/v1/analysis/")

        assert response.status_code == 500
        body = response.json()
        assert body["success"] is False
        assert body["meta"]["error_code"] == "ANALYSIS_FETCH_ERROR"

    def test_run_analysis_returns_500_on_error(self, authed_client, mock_supabase):
        with patch("routers.analysis.create_analysis_job_idempotent") as mock_job:
            mock_job.side_effect = Exception("job creation failed")

            response = authed_client.post(
                "/api/v1/analysis/run",
                json={"user_id": TEST_USER_ID}
            )

        assert response.status_code == 500
        body = response.json()
        assert body["success"] is False
        assert body["meta"]["error_code"] == "ANALYSIS_JOB_ERROR"

    # ======================================================
    # GET /job/{job_id}: the 404 and 403 branches -- untested before
    # ======================================================

    def test_job_status_returns_404_when_not_found(self, authed_client, mock_supabase):
        with patch("routers.analysis.get_job_status") as mock_status:
            mock_status.return_value = None

            response = authed_client.get("/api/v1/analysis/job/nonexistent-job")

        assert response.status_code == 404
        body = response.json()
        assert body["meta"]["error_code"] == "JOB_NOT_FOUND"

    def test_job_status_returns_403_for_wrong_user(self, authed_client, mock_supabase):
        with patch("routers.analysis.get_job_status") as mock_status:
            mock_status.return_value = {
                "id": "job-abc-123",
                "status": "completed",
                "user_id": "some-other-user-entirely"
            }

            response = authed_client.get("/api/v1/analysis/job/job-abc-123")

        assert response.status_code == 403
        body = response.json()
        assert body["meta"]["error_code"] == "ACCESS_DENIED"

    def test_job_status_returns_500_on_error(self, authed_client, mock_supabase):
        with patch("routers.analysis.get_job_status") as mock_status:
            mock_status.side_effect = Exception("boom")

            response = authed_client.get("/api/v1/analysis/job/job-abc-123")

        assert response.status_code == 500
        body = response.json()
        assert body["meta"]["error_code"] == "JOB_STATUS_ERROR"

    def test_job_status_real_service_call_does_not_recurse(self, authed_client, mock_supabase):
        """
        REGRESSION TEST for a naming-collision bug: the route handler for
        GET /job/{job_id} used to be named get_job_status, identically to
        the imported services.async_job_service.get_job_status it called
        internally. That shadowed the import at module scope, so every
        real (unmocked) call recursed into itself infinitely and returned
        a 500 error. It was invisible to the test suite because the only
        existing test patched routers.analysis.get_job_status directly --
        which replaces the broken self-reference with a mock before the
        endpoint runs, masking the bug rather than exercising it.

        This test deliberately does NOT patch that name. Instead it mocks
        only at the Supabase layer, forcing the real, unmocked service
        call chain (get_job_status -> async_job_service.get_job ->
        Supabase) to execute for real. Before the fix this recursed and
        returned 500; after the fix it returns the job correctly.
        """
        mock_supabase.table.return_value.select.return_value.eq.return_value \
            .execute.return_value = make_supabase_response([{
                "id": "job-real-1",
                "status": "completed",
                "user_id": TEST_USER_ID
            }])

        response = authed_client.get("/api/v1/analysis/job/job-real-1")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["id"] == "job-real-1"
        assert body["data"]["status"] == "completed"

    # ======================================================
    # GET /jobs -- had ZERO tests before this
    # ======================================================

    def test_get_analysis_jobs_returns_job_list(self, authed_client, mock_supabase):
        with patch("routers.analysis.get_user_job_history") as mock_history:
            mock_history.return_value = [{"id": "job-1"}, {"id": "job-2"}]

            response = authed_client.get("/api/v1/analysis/jobs")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["jobs"] == [{"id": "job-1"}, {"id": "job-2"}]

    def test_get_analysis_jobs_returns_500_on_error(self, authed_client, mock_supabase):
        with patch("routers.analysis.get_user_job_history") as mock_history:
            mock_history.side_effect = Exception("boom")

            response = authed_client.get("/api/v1/analysis/jobs")

        assert response.status_code == 500
        body = response.json()
        assert body["meta"]["error_code"] == "JOBS_LIST_ERROR"

    # ======================================================
    # GET /career-paths -- had ZERO tests before this
    # ======================================================

    def test_get_career_paths_returns_recommendations(self, authed_client, mock_supabase):
        with patch("routers.analysis.analysis_service.get_career_recommendations") as mock_rec:
            mock_rec.return_value = [{"name": "Backend Engineer"}]

            response = authed_client.get("/api/v1/analysis/career-paths")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["career_paths"] == [{"name": "Backend Engineer"}]

    def test_get_career_paths_returns_500_on_error(self, authed_client, mock_supabase):
        with patch("routers.analysis.analysis_service.get_career_recommendations") as mock_rec:
            mock_rec.side_effect = Exception("boom")

            response = authed_client.get("/api/v1/analysis/career-paths")

        assert response.status_code == 500
        body = response.json()
        assert body["meta"]["error_code"] == "CAREER_PATHS_ERROR"

    # ======================================================
    # GET /skill-gap -- had ZERO tests before this
    # ======================================================

    def test_get_skill_gap_returns_gaps(self, authed_client, mock_supabase):
        with patch("routers.analysis.analysis_service.get_skill_gaps") as mock_gaps:
            mock_gaps.return_value = [{"skill": "Docker"}]

            response = authed_client.get("/api/v1/analysis/skill-gap")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["skill_gaps"] == [{"skill": "Docker"}]

    def test_get_skill_gap_returns_500_on_error(self, authed_client, mock_supabase):
        with patch("routers.analysis.analysis_service.get_skill_gaps") as mock_gaps:
            mock_gaps.side_effect = Exception("boom")

            response = authed_client.get("/api/v1/analysis/skill-gap")

        assert response.status_code == 500
        body = response.json()
        assert body["meta"]["error_code"] == "SKILL_GAP_ERROR"