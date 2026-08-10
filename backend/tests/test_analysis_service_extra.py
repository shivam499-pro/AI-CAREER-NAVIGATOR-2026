"""
Additional tests for services/analysis_service.py filling in coverage gaps
left by tests/test_analysis_characterization.py:

- save_analysis: weaknesses / experience_level branches
- run_analysis: provider skipped when username is blank, Gemini failure path,
  unexpected-exception path (get_enriched_profile raises)
- get_career_recommendations: empty/missing cases, limit slicing, exception path
- get_skill_gaps: empty/missing cases, exception path
- _get_repository(): default factory wiring
"""
import pytest
from unittest.mock import patch, MagicMock

from services import analysis_service


# ─── save_analysis: extra field branches ──────────────────────────────────

def test_save_analysis_includes_weaknesses_in_payload_and_analysis_obj():
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True

    result = analysis_service.save_analysis(
        "u1", {"weaknesses": ["Communication"]}, repository=mock_repo
    )

    assert result is True
    payload = mock_repo.upsert.call_args[0][0]
    assert payload["weaknesses"] == ["Communication"]
    assert payload["analysis"]["weaknesses"] == ["Communication"]


def test_save_analysis_includes_experience_level_in_payload_and_analysis_obj():
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True

    result = analysis_service.save_analysis(
        "u1", {"experience_level": "Advanced"}, repository=mock_repo
    )

    assert result is True
    payload = mock_repo.upsert.call_args[0][0]
    assert payload["experience_level"] == "Advanced"
    assert payload["analysis"]["experience_level"] == "Advanced"


def test_save_analysis_with_no_recognized_fields_omits_analysis_key():
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True

    analysis_service.save_analysis("u1", {}, repository=mock_repo)

    payload = mock_repo.upsert.call_args[0][0]
    assert "analysis" not in payload
    assert payload["user_id"] == "u1"
    assert "updated_at" in payload


def test_save_analysis_career_paths_goes_to_top_level_only():
    """career_paths updates `data` but is deliberately excluded from the
    nested `analysis` object (per the source's conditional list)."""
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True

    analysis_service.save_analysis(
        "u1", {"career_paths": [{"name": "SWE"}]}, repository=mock_repo
    )

    payload = mock_repo.upsert.call_args[0][0]
    assert payload["career_paths"] == [{"name": "SWE"}]
    assert "analysis" not in payload


# ─── run_analysis: provider skipped when username blank ───────────────────

class _FakeProvider:
    def __init__(self, source_name, data=None):
        self.source_name = source_name
        self._data = data or {}
        self.fetch_called = False

    async def fetch_data(self, username):
        self.fetch_called = True
        return self._data


@pytest.mark.asyncio
async def test_run_analysis_skips_provider_fetch_when_username_missing():
    mock_repo = MagicMock()
    mock_repo.upsert.return_value = True
    provider = _FakeProvider("github", data={"repos": 5})

    with patch("services.analysis_service.get_enriched_profile") as mock_profile, \
         patch("services.gemini_service.run_combined_analysis") as mock_gemini:

        mock_profile.return_value = {"exists": True, "data": {}}  # no github_username
        mock_gemini.return_value = {"success": True, "data": {"career_paths": []}}

        result = await analysis_service.run_analysis(
            "u1", repository=mock_repo, providers=[provider]
        )

        assert result["success"] is True
        assert provider.fetch_called is False
        # gemini should have been called with empty github_data ({})
        _, kwargs = mock_gemini.call_args
        args = mock_gemini.call_args[0]
        assert args[0] == {}  # github_data positional arg


@pytest.mark.asyncio
async def test_run_analysis_returns_error_when_profile_missing():
    with patch("services.analysis_service.get_enriched_profile") as mock_profile:
        mock_profile.return_value = {"exists": False}

        result = await analysis_service.run_analysis("u1", repository=MagicMock())

        assert result["success"] is False
        assert "Profile not found" in result["error"]


@pytest.mark.asyncio
async def test_run_analysis_raises_and_reports_error_when_gemini_reports_failure():
    mock_repo = MagicMock()

    with patch("services.analysis_service.get_enriched_profile") as mock_profile, \
         patch("services.gemini_service.run_combined_analysis") as mock_gemini:

        mock_profile.return_value = {"exists": True, "data": {}}
        mock_gemini.return_value = {"success": False, "error": "Gemini quota exceeded"}

        result = await analysis_service.run_analysis(
            "u1", repository=mock_repo, providers=[]
        )

        assert result["success"] is False
        assert result["error"] == "Gemini quota exceeded"
        mock_repo.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_run_analysis_catches_unexpected_exception_and_returns_error_dict():
    with patch("services.analysis_service.get_enriched_profile") as mock_profile:
        mock_profile.side_effect = RuntimeError("profile service down")

        result = await analysis_service.run_analysis(
            "u1", repository=MagicMock(), providers=[]
        )

        assert result["success"] is False
        assert "profile service down" in result["error"]


# ─── get_career_recommendations ────────────────────────────────────────────

def test_get_career_recommendations_returns_empty_list_when_no_analysis():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = None

    result = analysis_service.get_career_recommendations("u1", repository=mock_repo)

    assert result == []


def test_get_career_recommendations_returns_empty_list_when_no_career_paths_key():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = {"skill_gaps": []}

    result = analysis_service.get_career_recommendations("u1", repository=mock_repo)

    assert result == []


def test_get_career_recommendations_applies_limit():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = {
        "career_paths": [{"name": f"Path{i}"} for i in range(10)]
    }

    result = analysis_service.get_career_recommendations("u1", limit=3, repository=mock_repo)

    assert len(result) == 3
    assert result[0]["name"] == "Path0"


def test_get_career_recommendations_swallows_exception_and_returns_empty_list():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.side_effect = Exception("db exploded")

    result = analysis_service.get_career_recommendations("u1", repository=mock_repo)

    assert result == []


# ─── get_skill_gaps ─────────────────────────────────────────────────────────

def test_get_skill_gaps_returns_empty_list_when_no_analysis():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = None

    result = analysis_service.get_skill_gaps("u1", repository=mock_repo)

    assert result == []


def test_get_skill_gaps_returns_skill_gaps_from_analysis():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = {"skill_gaps": [{"skill": "Docker"}]}

    result = analysis_service.get_skill_gaps("u1", repository=mock_repo)

    assert result == [{"skill": "Docker"}]


def test_get_skill_gaps_defaults_to_empty_list_when_key_missing():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.return_value = {"career_paths": []}

    result = analysis_service.get_skill_gaps("u1", repository=mock_repo)

    assert result == []


def test_get_skill_gaps_swallows_exception_and_returns_empty_list():
    mock_repo = MagicMock()
    mock_repo.get_by_user_id.side_effect = Exception("db exploded")

    result = analysis_service.get_skill_gaps("u1", repository=mock_repo)

    assert result == []


# ─── _get_repository default factory ───────────────────────────────────────

def test_get_repository_returns_a_supabase_analysis_repository_instance():
    from repositories.analysis_repository import SupabaseAnalysisRepository

    repo = analysis_service._get_repository()

    assert isinstance(repo, SupabaseAnalysisRepository)


def test_get_analysis_by_user_id_uses_default_repository_when_none_passed():
    with patch("services.analysis_service._get_repository") as mock_get_repo:
        mock_repo = MagicMock()
        mock_repo.get_by_user_id.return_value = {"user_id": "u1"}
        mock_get_repo.return_value = mock_repo

        result = analysis_service.get_analysis_by_user_id("u1")

        assert result == {"user_id": "u1"}
        mock_get_repo.assert_called_once()