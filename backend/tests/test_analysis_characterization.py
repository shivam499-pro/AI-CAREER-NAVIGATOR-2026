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


# ==========================================================
# save_analysis: weaknesses / experience_level branches
# (never hit -- the existing test's analysis_data doesn't include them)
# ==========================================================

def test_save_analysis_includes_weaknesses():
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True

    result = analysis_service.save_analysis(
        "test_user_id", {"weaknesses": ["Time management"]}, repository=mock_repo
    )

    args, _ = mock_repo.upsert.call_args
    payload = args[0]
    assert payload["weaknesses"] == ["Time management"]
    assert payload["analysis"]["weaknesses"] == ["Time management"]
    assert result is True


def test_save_analysis_includes_experience_level():
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True

    result = analysis_service.save_analysis(
        "test_user_id", {"experience_level": "Senior"}, repository=mock_repo
    )

    args, _ = mock_repo.upsert.call_args
    payload = args[0]
    assert payload["experience_level"] == "Senior"
    assert payload["analysis"]["experience_level"] == "Senior"
    assert result is True


# ==========================================================
# run_analysis: provider with no username -> empty-data fallback
# ==========================================================

@pytest.mark.asyncio
async def test_run_analysis_provider_without_username_gets_empty_data():
    """Only github_username is present -- leetcode's provider must fall
    back to {} rather than being skipped or raising."""
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True

    with patch('services.analysis_service.get_enriched_profile') as mock_profile, \
         patch('services.github_service.get_full_github_data') as mock_github, \
         patch('services.gemini_service.run_combined_analysis') as mock_gemini:

        mock_profile.return_value = {
            "exists": True,
            "data": {"github_username": "test"}  # no leetcode_username
        }
        mock_github.return_value = {"repos": 5}
        mock_gemini.return_value = {
            "success": True,
            "data": {
                "career_paths": [], "skill_gaps": [], "roadmap": {},
                "path_details": {}, "analysis": {"experience_level": "Intermediate"},
                "resume_score": {}, "salary_insights": {}, "top_companies": [],
                "certifications": []
            }
        }

        result = await analysis_service.run_analysis("test_user_id", repository=mock_repo)

        assert result["success"] is True

        github_data_arg, leetcode_data_arg = mock_gemini.call_args[0][0], mock_gemini.call_args[0][1]
        assert github_data_arg == {"repos": 5}
        assert leetcode_data_arg == {}


# ==========================================================
# run_analysis: Gemini failure -> raised, then caught by the
# outer except and converted to a graceful error response
# ==========================================================

@pytest.mark.asyncio
async def test_run_analysis_gemini_failure_is_caught_and_returns_error():
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
            "success": False,
            "error": "Gemini rate limit exceeded"
        }

        result = await analysis_service.run_analysis("test_user_id", repository=mock_repo)

        assert result["success"] is False
        assert result["error"] == "Gemini rate limit exceeded"
        # must not save partial/bad data when analysis failed
        mock_repo.upsert.assert_not_called()


# ==========================================================
# get_career_recommendations -- had ZERO tests before this
# ==========================================================

def test_get_career_recommendations_returns_sliced_list():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = {
        "career_paths": [{"name": f"Path{i}"} for i in range(10)]
    }

    result = analysis_service.get_career_recommendations("user-1", limit=3, repository=mock_repo)

    assert len(result) == 3
    assert result[0]["name"] == "Path0"


def test_get_career_recommendations_no_analysis_returns_empty():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = None

    result = analysis_service.get_career_recommendations("user-1", repository=mock_repo)

    assert result == []


def test_get_career_recommendations_no_career_paths_returns_empty():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = {"career_paths": []}

    result = analysis_service.get_career_recommendations("user-1", repository=mock_repo)

    assert result == []


def test_get_career_recommendations_exception_returns_empty():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.side_effect = Exception("db error")

    result = analysis_service.get_career_recommendations("user-1", repository=mock_repo)

    assert result == []


# ==========================================================
# get_skill_gaps -- had ZERO tests before this
# ==========================================================

def test_get_skill_gaps_returns_list():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = {"skill_gaps": [{"skill": "Docker"}]}

    result = analysis_service.get_skill_gaps("user-1", repository=mock_repo)

    assert result == [{"skill": "Docker"}]


def test_get_skill_gaps_no_analysis_returns_empty():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = None

    result = analysis_service.get_skill_gaps("user-1", repository=mock_repo)

    assert result == []


def test_get_skill_gaps_exception_returns_empty():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.side_effect = Exception("db error")

    result = analysis_service.get_skill_gaps("user-1", repository=mock_repo)

    assert result == []


# ==========================================================
# _get_repository(): the default-factory path -- every other test in
# this file injects repository= explicitly, so this default branch
# (used by real, non-test callers) was never actually invoked
# ==========================================================

def test_get_repository_returns_supabase_repository():
    from repositories.analysis_repository import SupabaseAnalysisRepository

    repo = analysis_service._get_repository()

    assert isinstance(repo, SupabaseAnalysisRepository)


# ==========================================================
# run_analysis: profile-not-found early return
# (every existing test provides exists: True)
# ==========================================================

@pytest.mark.asyncio
async def test_run_analysis_profile_not_found_returns_error():
    with patch('services.analysis_service.get_enriched_profile') as mock_profile:
        mock_profile.return_value = {"exists": False}

        result = await analysis_service.run_analysis("test_user_id")

        assert result["success"] is False
        assert result["error"] == "Profile not found. Please complete your profile first."
def test_analysis_model_normalizes_singular_skill_gap_key():
    """Some AI responses use the singular 'skill_gap' key instead of the
    canonical 'skill_gaps' -- the model should normalize it transparently."""
    response_with_singular_key = {
        "id": "123",
        "user_id": "test_user_id",
        "strengths": ["Python"],
        "weaknesses": ["Java"],
        "experience_level": "Beginner",
        "career_paths": [
            {"name": "Backend Developer", "match_percentage": 85, "reason": "Good"}
        ],
        "skill_gap": [
            {"skill": "Docker", "have": False, "priority": 1}
        ],
        "created_at": "2026-05-26T00:00:00Z"
    }

    model = AnalysisResult(**response_with_singular_key)

    assert len(model.skill_gaps) == 1
    assert model.skill_gaps[0].skill == "Docker"