import pytest
from unittest.mock import patch, MagicMock
from services import analysis_service
from models.analysis import AnalysisResult


@pytest.mark.asyncio
async def test_run_analysis_returns_expected_schema():
    # 1. Backend — analysis_service output shape
    # get_supabase no longer lives in analysis_service — it's in the repository
    # So we patch the repository's upsert method instead
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True

    with patch('services.analysis_service.get_enriched_profile') as mock_profile, \
         patch('services.github_service.get_full_github_data') as mock_github, \
         patch('services.leetcode_service.get_full_leetcode_data') as mock_leetcode, \
         patch('services.gemini_service.run_combined_analysis') as mock_gemini:

        mock_profile.return_value = {
            "exists": True,
            "data": {"github_username": "test", "leetcode_username": "test"}
        }
        mock_github.return_value = {}
        mock_leetcode.return_value = {}
        mock_gemini.return_value = {
            "success": True,
            "data": {
                "career_paths": [{"name": "Software Engineer", "match_percentage": 90, "reason": "Good match"}],
                "skill_gaps": [{"skill": "Python", "have": False, "priority": 1}],
                "roadmap": {},
                "path_details": {},
                "analysis": {"experience_level": "Intermediate"},
                "resume_score": {},
                "salary_insights": {},
                "top_companies": [],
                "certifications": []
            }
        }

        # Pass mock_repo directly — no need to patch get_supabase at all
        result = await analysis_service.run_analysis("test_user_id", repository=mock_repo)

        assert result["success"] is True
        assert "analysis" in result

        analysis_data = result["analysis"]
        assert "career_paths" in analysis_data
        assert "skill_gaps" in analysis_data
        assert "roadmap" in analysis_data
        assert "path_details" in analysis_data
        assert "analysis" in analysis_data
        assert "experience_level" in analysis_data["analysis"]

        # Also verify the repository's upsert was called once
        mock_repo.upsert.assert_called_once()


def test_analysis_model_accepts_real_gemini_response():
    # 2. After Phase 1 LSP fix — normalizers handle the chaos, this MUST pass
    real_gemini_response = {
        "id": "123",
        "user_id": "test_user_id",
        "strengths": ["Python"],
        "weaknesses": ["Java"],
        "experience_level": "Beginner",
        "career_paths": [
            {"career_name": "Backend Developer", "match_percentage": 85, "reason": "Good"},
            {"title": "Frontend Developer", "match": 70, "justification": "Okay"}
        ],
        "skill_gaps": [
            {"skill_name": "Docker", "has": False, "priority_level": 1},
            {"name": "Kubernetes", "owned": False, "level": 2}
        ],
        "created_at": "2026-05-26T00:00:00Z"
    }

    model = AnalysisResult(**real_gemini_response)

    assert model.career_paths[0].name == "Backend Developer"
    assert model.career_paths[1].name == "Frontend Developer"
    assert model.career_paths[1].match_percentage == 70
    assert model.skill_gaps[0].skill == "Docker"
    assert model.skill_gaps[0].have is False
    assert model.skill_gaps[1].skill == "Kubernetes"


def test_analysis_repository_saves_and_retrieves():
    # 3. DB write — now tests via mock repository directly, not via get_supabase
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True

    analysis_data = {
        "strengths": ["Python"],
        "career_paths": [],
        "skill_gaps": []
    }

    result = analysis_service.save_analysis("test_user_id", analysis_data, repository=mock_repo)

    # Assert repository upsert was called
    mock_repo.upsert.assert_called_once()

    # Assert the payload shape
    args, kwargs = mock_repo.upsert.call_args
    payload = args[0]
    assert payload["user_id"] == "test_user_id"
    assert "updated_at" in payload
    assert "strengths" in payload
    assert "career_paths" in payload
    assert "skill_gaps" in payload
    assert "analysis" in payload
    assert payload["analysis"]["strengths"] == ["Python"]
    assert result is True