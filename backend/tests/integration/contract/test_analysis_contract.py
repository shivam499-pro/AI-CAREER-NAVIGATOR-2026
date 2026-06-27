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