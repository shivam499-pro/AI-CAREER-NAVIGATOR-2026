"""
Live Analysis Flow Test
Tests profile save → retrieve, and analysis repository upsert → get,
against the REAL Supabase test project. Gemini is still mocked here
since this test is about the database layer, not the AI layer.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

pytestmark = pytest.mark.live

client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.integration
class TestAnalysisFlowLive:

    def test_profile_save_then_retrieve(self, live_auth_headers, live_test_user):
        """
        Full real-DB cycle: POST /profile/save → GET /profile/me
        Verifies the upsert actually persisted and the nested response
        shape (json.data.profile.data) survives a real round trip.
        """
        profile_data = {
            "user_id": live_test_user["id"],
            "user_type": "student",
            "github_username": "integration-test-user",
            "career_goal": "Full Stack Developer",
            "extra_skills": ["React", "Python"],
        }

        save_response = client.post(
            "/api/v1/profile/save", json=profile_data, headers=live_auth_headers
        )
        assert save_response.status_code in (200, 201), save_response.text

        get_response = client.get("/api/v1/profile/me", headers=live_auth_headers)
        assert get_response.status_code == 200

        body = get_response.json()
        data = body.get("data", {}).get("profile", {}).get("data", {})
        assert data.get("github_username") == "integration-test-user"
        assert data.get("career_goal") == "Full Stack Developer"

    def test_analysis_repository_upsert_and_get_cycle(self, live_supabase, live_test_user):
        """
        Tests SupabaseAnalysisRepository directly against the real DB —
        bypassing the API layer to isolate the repository/DB contract.
        Catches issues mocks cannot: RLS policy misconfiguration,
        on_conflict behavior, JSONB serialization round-trip correctness.
        """
        from repositories.analysis_repository import SupabaseAnalysisRepository

        repo = SupabaseAnalysisRepository()
        print("\nLIVE URL:", live_supabase.supabase_url)
        print("REPO URL:", repo._get_supabase().supabase_url)

        analysis_data = {
            "user_id": live_test_user["id"],
            "career_paths": [{"name": "Backend Engineer", "match_percentage": 80}],
            "skill_gaps": ["Docker"],
            "experience_level": "Junior",
        }

        repo = SupabaseAnalysisRepository()

        print("\nLIVE URL:", live_supabase.supabase_url)
        print("REPO URL:", repo._get_supabase().supabase_url)
        
        success = repo.upsert(analysis_data)
        assert success, "Repository upsert failed against real Supabase test project"

        retrieved = repo.get_by_user_id(live_test_user["id"])
        assert retrieved is not None, "get_by_user_id returned None after a successful upsert"
        assert retrieved["experience_level"] == "Junior"
        assert len(retrieved["career_paths"]) == 1
        assert retrieved["career_paths"][0]["name"] == "Backend Engineer"

    def test_analysis_upsert_overwrites_not_duplicates(self, live_supabase, live_test_user):
        """
        The schema has a UNIQUE constraint on analyses.user_id.
        This proves upsert respects on_conflict and doesn't create
        duplicate rows for the same user — something only a real
        constraint check can verify.
        """
        from repositories.analysis_repository import SupabaseAnalysisRepository

        repo = SupabaseAnalysisRepository()

        repo.upsert({
            "user_id": live_test_user["id"],
            "experience_level": "Junior",
            "career_paths": [],
        })
        repo.upsert({
            "user_id": live_test_user["id"],
            "experience_level": "Mid",
            "career_paths": [],
        })

        rows = (
            live_supabase.table("analyses")
            .select("*")
            .eq("user_id", live_test_user["id"])
            .execute()
        )
        assert len(rows.data) == 1, "Upsert created a duplicate row instead of overwriting"
        assert rows.data[0]["experience_level"] == "Mid"
    def test_analysis_save_and_retrieve_cycle(self, live_test_user, live_supabase):
        """
        Save analysis to DB → retrieve via API → verify shape matches.
        Tests SupabaseAnalysisRepository.upsert() and get_by_user_id().
        """
        from repositories.analysis_repository import SupabaseAnalysisRepository
        
        repo = SupabaseAnalysisRepository()
        
        analysis_data = {
            "user_id": live_test_user["id"],
            "career_paths": [{"name": "Backend Engineer", "match_percentage": 80}],
            "skill_gaps": ["Docker"],
            "experience_level": "Junior",
        }
        
        # Save via repository
        success = repo.upsert(analysis_data)
        assert success, "Repository upsert failed"
        
        # Retrieve via repository
        retrieved = repo.get_by_user_id(live_test_user["id"])
        assert retrieved is not None, "Repository get_by_user_id returned None"
        assert retrieved["experience_level"] == "Junior"
        assert len(retrieved["career_paths"]) == 1