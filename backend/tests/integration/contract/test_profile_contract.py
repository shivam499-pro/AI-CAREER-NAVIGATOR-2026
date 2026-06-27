"""
Profile Contract Tests
useProfile.ts accesses: json.data.profile.data (deeply nested)
ProgressTracker.tsx accesses: result.data.progress.total/steps/status
"""
import pytest
from unittest.mock import patch, MagicMock
from tests.integration.conftest import TEST_USER_ID, make_supabase_response

class TestProfileContract:

    def test_get_profile_response_nested_shape(self, authed_client, mock_supabase):
        """
        CRITICAL: useProfile.loadProfile() parses:
        const data = json?.data?.profile?.data || {}
        
        If nesting is wrong, ALL profile fields are empty strings silently.
        """
        mock_profile_data = {
            "user_id": TEST_USER_ID,
            "user_type": "student",
            "github_username": "testuser",
            "career_goal": "Full Stack Developer",
        }
        mock_supabase.table.return_value.select.return_value\
            .eq.return_value.execute.return_value = \
            make_supabase_response([mock_profile_data])
        
        response = authed_client.get("/api/v1/profile/me")
        
        assert response.status_code == 200
        body = response.json()
        
        # Verify the exact nesting useProfile expects
        assert "data" in body, "Top-level 'data' key missing"
        assert "profile" in body["data"], "'profile' key missing from data"
        assert "data" in body["data"]["profile"], "Inner 'data' key missing from profile"

    def test_save_profile_accepts_all_form_fields(self, authed_client, mock_supabase):
        """
        useProfile.saveProfile() sends ALL ProfileFormData fields.
        Backend must not reject valid optional fields as 422.
        """
        full_profile = {
            "user_type": "student",
            "college_name": "MIT",
            "degree": "B.Tech",
            "branch": "Computer Science",
            "year_of_study": "3rd Year",
            "graduation_year": 2026,
            "cgpa": "8.5",
            "current_job_title": "",
            "current_company": "",
            "years_of_experience": 0,
            "current_tech_stack": ["React", "Node.js"],
            "reason_for_switching": "",
            "career_goal": "Full Stack Developer",
            "target_companies": ["Google", "Microsoft"],
            "preferred_work_type": "remote",
            "job_search_timeline": "6 months",
            "preferred_location": "Bangalore",
            "extra_skills": ["Python", "Docker"],
            "github_username": "testuser",
            "leetcode_username": "testuser",
            "linkedin_url": "https://linkedin.com/in/test",
        }
        
        mock_supabase.table.return_value.upsert.return_value\
            .execute.return_value = make_supabase_response([{"user_id": TEST_USER_ID}])
        
        response = authed_client.post(
            "/api/v1/profile/save",
            json={"user_id": TEST_USER_ID, **full_profile}
        )
        
        # Must not be 422 — all fields are valid
        assert response.status_code != 422, \
            f"Valid profile fields were rejected: {response.json()}"
        assert response.status_code in (200, 201)

    def test_progress_response_has_required_fields(self, authed_client, mock_supabase):
        """
        ProgressTracker.tsx parses: result.data.progress
        Then accesses: data.total, data.steps, data.status
        """
        mock_supabase.table.return_value.select.return_value\
            .eq.return_value.execute.return_value = \
            make_supabase_response([{"user_id": TEST_USER_ID}])
        
        response = authed_client.get("/api/v1/profile/progress")
        
        assert response.status_code == 200
        body = response.json()
        progress = body.get("data", {}).get("progress", body)
        
        assert "total" in progress, "total field missing — ProgressTracker shows undefined%"
        assert "steps" in progress, "steps array missing — ProgressTracker renders nothing"
        assert "status" in progress, "status field missing — badge not shown"
        assert isinstance(progress["steps"], list)