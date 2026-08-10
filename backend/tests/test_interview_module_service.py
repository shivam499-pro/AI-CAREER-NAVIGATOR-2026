"""
Tests for modules/interview/service.py (InterviewModuleService) and
modules/interview/repository.py (InterviewRepository).

Neither had a dedicated test file before. routers/interview.py instantiates
InterviewModuleService at import time and calls its methods, so these were
partially exercised indirectly through router/integration tests, but several
branches — the `supabase` property, saving non-empty interview rows, the
"profile found" happy path of prepare_interview_profile, and the repository's
save_interview_rows body — were never actually hit.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from modules.interview.service import InterviewModuleService
from modules.interview.repository import InterviewRepository


# ─── InterviewModuleService.get_or_create_session ──────────────────────────

def test_get_or_create_session_returns_same_id_for_same_user_and_path():
    service = InterviewModuleService()

    first = service.get_or_create_session("user1", "backend")
    second = service.get_or_create_session("user1", "backend")

    assert first == second


def test_get_or_create_session_returns_different_ids_for_different_paths():
    service = InterviewModuleService()

    backend_id = service.get_or_create_session("user1", "backend")
    frontend_id = service.get_or_create_session("user1", "frontend")

    assert backend_id != frontend_id


# ─── InterviewModuleService.supabase property ──────────────────────────────

def test_supabase_property_delegates_to_get_supabase():
    service = InterviewModuleService()
    fake_client = MagicMock()

    with patch("modules.interview.service.get_supabase", return_value=fake_client) as mock_get:
        result = service.supabase

        assert result is fake_client
        mock_get.assert_called_once()


# ─── InterviewModuleService.save_session_data ──────────────────────────────

@pytest.mark.asyncio
async def test_save_session_data_saves_session_only_when_rows_empty():
    service = InterviewModuleService()
    service.repository = MagicMock()
    service.repository.save_interview_session = AsyncMock(return_value=None)
    service.repository.save_interview_rows = AsyncMock(return_value=None)

    await service.save_session_data(session_data={"user_id": "u1"}, interview_rows=[])

    service.repository.save_interview_session.assert_awaited_once_with({"user_id": "u1"})
    service.repository.save_interview_rows.assert_not_called()


@pytest.mark.asyncio
async def test_save_session_data_saves_rows_when_present():
    service = InterviewModuleService()
    service.repository = MagicMock()
    service.repository.save_interview_session = AsyncMock(return_value=None)
    service.repository.save_interview_rows = AsyncMock(return_value=None)

    rows = [{"question": "Q1"}, {"question": "Q2"}]
    await service.save_session_data(session_data={"user_id": "u1"}, interview_rows=rows)

    service.repository.save_interview_session.assert_awaited_once_with({"user_id": "u1"})
    service.repository.save_interview_rows.assert_awaited_once_with(rows)


# ─── InterviewModuleService.prepare_interview_profile ──────────────────────

@pytest.mark.asyncio
async def test_prepare_interview_profile_returns_empty_dict_when_no_profile():
    service = InterviewModuleService()
    service.repository = MagicMock()

    profile_response = MagicMock(data=[])
    analysis_response = MagicMock(data=[])
    service.repository.get_profile_by_user_id = AsyncMock(return_value=profile_response)
    service.repository.get_analysis_by_user_id = AsyncMock(return_value=analysis_response)

    result = await service.prepare_interview_profile("u1")

    assert result == {}


@pytest.mark.asyncio
async def test_prepare_interview_profile_builds_full_profile_when_data_present():
    service = InterviewModuleService()
    service.repository = MagicMock()

    profile_row = {
        "college_name": "MIT",
        "degree": "BSc",
        "branch": "CS",
        "extra_skills": ["Docker"],
        "experience": ["Intern at X"],
        "certificates": ["AWS Cert"],
        "career_goal": "Backend Engineer",
        "resume_text": "Resume text here",
        "github_username": "octocat",
    }
    analysis_row = {
        "analysis": {"strengths": ["Python", "SQL"]},
        "career_paths": [{"name": "Backend Engineer"}],
    }

    profile_response = MagicMock(data=[profile_row])
    analysis_response = MagicMock(data=[analysis_row])
    service.repository.get_profile_by_user_id = AsyncMock(return_value=profile_response)
    service.repository.get_analysis_by_user_id = AsyncMock(return_value=analysis_response)

    result = await service.prepare_interview_profile("u1")

    assert result["college_name"] == "MIT"
    assert result["degree"] == "BSc"
    assert result["branch"] == "CS"
    assert result["extra_skills"] == ["Docker"]
    assert result["experience"] == ["Intern at X"]
    assert result["certificates"] == ["AWS Cert"]
    assert result["career_goal"] == "Backend Engineer"
    assert result["resume_text"] == "Resume text here"
    assert result["github_username"] == "octocat"
    assert result["strengths"] == ["Python", "SQL"]
    assert result["career_paths"] == [{"name": "Backend Engineer"}]


@pytest.mark.asyncio
async def test_prepare_interview_profile_defaults_analysis_to_empty_dict_when_no_analysis_rows():
    """Profile exists but the analysis table has no rows for this user —
    analysis_data should default to {} rather than raising."""
    service = InterviewModuleService()
    service.repository = MagicMock()

    profile_row = {"college_name": "MIT"}
    profile_response = MagicMock(data=[profile_row])
    analysis_response = MagicMock(data=[])
    service.repository.get_profile_by_user_id = AsyncMock(return_value=profile_response)
    service.repository.get_analysis_by_user_id = AsyncMock(return_value=analysis_response)

    result = await service.prepare_interview_profile("u1")

    assert result["college_name"] == "MIT"
    assert result["strengths"] == []
    assert result["career_paths"] == []


# ─── InterviewRepository ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_profile_by_user_id_queries_profiles_table():
    repo = InterviewRepository()
    fake_response = MagicMock(data=[{"user_id": "u1"}])
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = fake_response

    with patch("modules.interview.repository.get_supabase", return_value=mock_supabase):
        result = await repo.get_profile_by_user_id("u1")

    assert result is fake_response
    mock_supabase.table.assert_called_once_with("profiles")
    mock_supabase.table.return_value.select.assert_called_once_with("*")
    mock_supabase.table.return_value.select.return_value.eq.assert_called_once_with("user_id", "u1")


@pytest.mark.asyncio
async def test_get_analysis_by_user_id_queries_analyses_table():
    repo = InterviewRepository()
    fake_response = MagicMock(data=[{"user_id": "u1"}])
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = fake_response

    with patch("modules.interview.repository.get_supabase", return_value=mock_supabase):
        result = await repo.get_analysis_by_user_id("u1")

    assert result is fake_response
    mock_supabase.table.assert_called_once_with("analyses")


@pytest.mark.asyncio
async def test_save_interview_session_inserts_into_interview_sessions_table():
    repo = InterviewRepository()
    fake_response = MagicMock(data=[{"id": "s1"}])
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = fake_response

    with patch("modules.interview.repository.get_supabase", return_value=mock_supabase):
        result = await repo.save_interview_session({"user_id": "u1"})

    assert result is fake_response
    mock_supabase.table.assert_called_once_with("interview_sessions")
    mock_supabase.table.return_value.insert.assert_called_once_with({"user_id": "u1"})


@pytest.mark.asyncio
async def test_save_interview_rows_inserts_into_interviews_table():
    repo = InterviewRepository()
    fake_response = MagicMock(data=[{"id": "r1"}, {"id": "r2"}])
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = fake_response

    rows = [{"question": "Q1"}, {"question": "Q2"}]
    with patch("modules.interview.repository.get_supabase", return_value=mock_supabase):
        result = await repo.save_interview_rows(rows)

    assert result is fake_response
    mock_supabase.table.assert_called_once_with("interviews")
    mock_supabase.table.return_value.insert.assert_called_once_with(rows)