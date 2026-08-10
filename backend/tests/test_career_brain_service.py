import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import asyncio
import os
import httpx
from services.career_brain_service import fetch_interview_sessions
from services.career_brain_service import fetch_analysis, fetch_profile
from services.career_brain_service import get_career_brain

from services.career_brain_service import (
    analyze_skills,
    calculate_job_readiness_score,
    generate_behavioral_insights,
    generate_recommendations,
    detect_risks,
    get_progress_summary,
    clear_cache,
)

class MockResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class MockClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        return self.response


@pytest.mark.asyncio
async def test_fetch_profile_non_200(mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_profile("url", {}, "u1")

    assert result is None

@pytest.mark.asyncio
async def test_fetch_analysis_empty_list(mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_analysis("url", {}, "u1")

    assert result is None
    

@pytest.mark.asyncio
async def test_fetch_interview_sessions_failure(mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_interview_sessions("url", {}, "u1")

    assert result == []

@pytest.mark.asyncio
async def test_fetch_profile_success(mocker):
    from services.career_brain_service import fetch_profile

    response = MockResponse(
        200,
        [{"user_id": "u1"}]
    )

    mocker.patch(
        "services.career_brain_service.httpx.AsyncClient",
        return_value=MockClient(response)
    )

    result = await fetch_profile(
        "http://test",
        {},
        "u1"
    )

    assert result["user_id"] == "u1"


from services.career_brain_service import fetch_job_applications

@pytest.mark.asyncio
async def test_fetch_job_applications_empty(mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_job_applications("url", {}, "u1")

    assert result == []

from services.career_brain_service import fetch_saved_jobs

@pytest.mark.asyncio
async def test_fetch_saved_jobs_failure(mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_saved_jobs("url", {}, "u1")

    assert result == []

from services.career_brain_service import fetch_user_rank

@pytest.mark.asyncio
async def test_fetch_user_rank_empty(mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_user_rank("url", {}, "u1")

    assert result is None




@pytest.mark.asyncio
async def test_fetch_profile_empty(mocker):
    from services.career_brain_service import fetch_profile

    response = MockResponse(200, [])

    mocker.patch(
        "services.career_brain_service.httpx.AsyncClient",
        return_value=MockClient(response)
    )

    result = await fetch_profile(
        "http://test",
        {},
        "u1"
    )

    assert result is None


@pytest.mark.asyncio
async def test_fetch_profile_failure(mocker):
    from services.career_brain_service import fetch_profile

    response = MockResponse(500, [])

    mocker.patch(
        "services.career_brain_service.httpx.AsyncClient",
        return_value=MockClient(response)
    )

    result = await fetch_profile(
        "http://test",
        {},
        "u1"
    )

    assert result is None

@pytest.mark.asyncio
async def test_get_career_brain_missing_env(monkeypatch):
    from services.career_brain_service import get_career_brain

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    result = await get_career_brain("u1")

    assert result["error"] == "Database not configured"

@pytest.mark.asyncio
async def test_get_career_brain_missing_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    result = await get_career_brain("u1")

    assert result["error"] == "Database not configured"

@pytest.mark.asyncio
async def test_get_career_brain_success(mocker, monkeypatch):
    # Fake env
    monkeypatch.setenv("SUPABASE_URL", "http://test")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")

    # Mock fetchers
    mocker.patch("services.career_brain_service.fetch_profile", return_value={"user_id": "u1"})
    mocker.patch("services.career_brain_service.fetch_analysis", return_value={"skill_gaps": []})
    mocker.patch("services.career_brain_service.fetch_job_applications", return_value=[{"status": "applied"}])
    mocker.patch("services.career_brain_service.fetch_saved_jobs", return_value=[])
    mocker.patch("services.career_brain_service.fetch_interview_sessions", return_value=[{"total_score": 80}])
    mocker.patch("services.career_brain_service.fetch_user_streak", return_value={"current_streak": 5})
    mocker.patch("services.career_brain_service.fetch_user_rank", return_value={"rank_title": "Pro", "level": 2, "xp": 100})

    result = await get_career_brain("u1", use_cache=False)

    assert "job_readiness_score" in result
    assert "skill_insights" in result
    assert "recommendations" in result
    assert result["rank"] == "Pro"
    assert result["level"] == 2


@pytest.mark.asyncio
async def test_get_career_brain_cache_hit(mocker, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://test")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")

    # mock ALL dependencies
    mocker.patch("services.career_brain_service.fetch_profile", return_value={"user_id": "u1"})
    mocker.patch("services.career_brain_service.fetch_analysis", return_value={"skill_gaps": []})
    mocker.patch("services.career_brain_service.fetch_job_applications", return_value=[])
    mocker.patch("services.career_brain_service.fetch_saved_jobs", return_value=[])
    mocker.patch("services.career_brain_service.fetch_interview_sessions", return_value=[])
    mocker.patch("services.career_brain_service.fetch_user_streak", return_value=None)
    mocker.patch("services.career_brain_service.fetch_user_rank", return_value=None)

    # first call populates cache
    result1 = await get_career_brain("u1", use_cache=True)

    # second call should hit cache
    result2 = await get_career_brain("u1", use_cache=True)

    assert result1 == result2

@pytest.mark.asyncio
async def test_get_career_brain_cache_bypass(mocker, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://test")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")

    fetch_profile = mocker.patch(
        "services.career_brain_service.fetch_profile",
        return_value={"user_id": "u1"}
    )
    mocker.patch("services.career_brain_service.fetch_analysis", return_value={"skill_gaps": []})
    mocker.patch("services.career_brain_service.fetch_job_applications", return_value=[])
    mocker.patch("services.career_brain_service.fetch_saved_jobs", return_value=[])
    mocker.patch("services.career_brain_service.fetch_interview_sessions", return_value=[])
    mocker.patch("services.career_brain_service.fetch_user_streak", return_value=None)
    mocker.patch("services.career_brain_service.fetch_user_rank", return_value=None)

    await get_career_brain("u1", use_cache=False)
    await get_career_brain("u1", use_cache=False)

    assert fetch_profile.call_count == 2
# ==========================================================
# analyze_skills
# ==========================================================

def test_analyze_skills_profile_only():
    profile = {
        "current_tech_stack": ["Python", "FastAPI"],
        "extra_skills": ["React"]
    }

    result = analyze_skills(profile, None, [])

    assert "python" in result["strong"]
    assert "fastapi" in result["strong"]
    assert "react" in result["strong"]
    assert result["weak"] == []
    assert result["missing"] == []


def test_analyze_skills_with_analysis_and_applications():
    profile = {"current_tech_stack": ["Python"]}

    analysis = {
        "strengths": ["System Design"],
        "skill_gaps": ["Docker", "Kubernetes"]
    }

    applications = [
        {"missing_skills": ["Docker", "AWS"]},
        {"missing_skills": ["Docker"]},
    ]

    result = analyze_skills(profile, analysis, applications)

    assert "python" in result["strong"]
    assert "system design" in result["strong"]

    assert "docker" in result["weak"]
    assert "kubernetes" in result["weak"]

    assert result["missing"][0] == "docker"


def test_analyze_skills_skill_gap_dict():
    analysis = {
        "skill_gaps": {
            "backend": ["FastAPI"],
            "cloud": ["AWS"]
        }
    }

    result = analyze_skills(None, analysis, [])

    assert "fastapi" in result["weak"]
    assert "aws" in result["weak"]


# ==========================================================
# calculate_job_readiness_score
# ==========================================================

def test_job_readiness_perfect_profile():
    profile = {
        "current_tech_stack": ["Python"],
        "resume_text": "resume",
        "github_username": "user",
        "leetcode_username": "user",
    }

    analysis = {"skill_gaps": []}

    applications = [{"status": "applied"} for _ in range(10)]

    interviews = [{"total_score": 90} for _ in range(5)]

    score = calculate_job_readiness_score(
        profile,
        analysis,
        applications,
        interviews
    )

    assert score == 100


def test_job_readiness_with_skill_gaps():
    analysis = {
        "skill_gaps": [
            "Docker",
            "AWS",
            "Kubernetes"
        ]
    }

    score = calculate_job_readiness_score(
        None,
        analysis,
        [],
        []
    )

    assert score < 100
    assert score > 0


# ==========================================================
# behavioral insights
# ==========================================================

def test_behavioral_insights_high_rejection():
    applications = [
        {"status": "rejected"},
        {"status": "rejected"},
        {"status": "rejected"},
        {"status": "rejected"},
        {"status": "applied"},
    ]

    insights = generate_behavioral_insights(
        applications,
        [],
        None,
        []
    )

    assert any("rejections" in i.lower() for i in insights)


def test_behavioral_insights_improving_scores():
    interviews = [
        {"total_score": 40},
        {"total_score": 50},
        {"total_score": 80},
    ]

    insights = generate_behavioral_insights(
        [],
        interviews,
        None,
        []
    )

    assert any("improving" in i.lower() for i in insights)


def test_behavioral_insights_streak():
    streak = {"current_streak": 10}

    insights = generate_behavioral_insights(
        [],
        [],
        streak,
        []
    )

    assert any("10 day streak" in i.lower() for i in insights)


# ==========================================================
# recommendations
# ==========================================================

def test_generate_recommendations_low_readiness():
    recommendations = generate_recommendations(
        {},
        40,
        [],
        ["docker", "aws"],
        ["communication"]
    )

    assert len(recommendations) > 0

    joined = " ".join(recommendations).lower()

    assert "docker" in joined
    assert "communication" in joined


def test_generate_recommendations_high_readiness():
    recommendations = generate_recommendations(
        {},
        90,
        [{"status": "applied"} for _ in range(5)],
        [],
        []
    )

    assert any("job readiness is high" in r.lower()
               for r in recommendations)


# ==========================================================
# detect_risks
# ==========================================================

def test_detect_risks_rejection_streak():
    applications = [
        {"status": "rejected"},
        {"status": "rejected"},
        {"status": "rejected"},
        {"status": "rejected"},
        {"status": "applied"},
    ]

    alerts = detect_risks(
        applications,
        [],
        None,
        None
    )

    assert len(alerts) > 0


def test_detect_risks_old_interview():
    old_date = (
        datetime.utcnow() - timedelta(days=20)
    ).isoformat()

    alerts = detect_risks(
        [],
        [{"created_at": old_date}],
        None,
        None
    )

    assert any("no interview practice" in a.lower()
               for a in alerts)


def test_detect_risks_low_streak():
    alerts = detect_risks(
        [{"status": "applied"}],
        [],
        {"current_streak": 1},
        None
    )

    assert any("low consistency" in a.lower()
               for a in alerts)


# ==========================================================
# progress summary
# ==========================================================

def test_progress_summary():
    apps = [
        {"status": "applied"},
        {"status": "interview"},
        {"status": "offer"},
        {"status": "rejected"},
    ]

    result = get_progress_summary(
        apps,
        [{}, {}],
        [{}, {}]
    )

    assert result["total_applications"] == 4
    assert result["total_interviews"] == 1
    assert result["total_offers"] == 1
    assert result["total_rejections"] == 1
    assert result["saved_jobs"] == 2
    assert result["interview_sessions"] == 2


# ==========================================================
# clear cache
# ==========================================================

def test_clear_cache():
    clear_cache()


# ==========================================================
# additional coverage: fetch_* non-200 / success branches
# ==========================================================

@pytest.mark.asyncio
async def test_fetch_analysis_non_200(mocker):
    """Line 45: the fallback `return None` when status_code != 200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_analysis("url", {}, "u1")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_interview_sessions_success(mocker):
    """Line 56: the success path `return resp.json()` was never hit --
    the only existing test for this fetcher covered the failure path."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": 1, "total_score": 75}]

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_interview_sessions("url", {}, "u1")

    assert result == [{"id": 1, "total_score": 75}]


@pytest.mark.asyncio
async def test_fetch_job_applications_non_200(mocker):
    """Line 69: fallback `return []` for a non-200 response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_job_applications("url", {}, "u1")

    assert result == []


@pytest.mark.asyncio
async def test_fetch_saved_jobs_success(mocker):
    """Line 80: success path -- only the failure path was tested before."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"job_id": "j1"}]

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_saved_jobs("url", {}, "u1")

    assert result == [{"job_id": "j1"}]


@pytest.mark.asyncio
async def test_fetch_user_rank_non_200(mocker):
    """Line 107: fallback `return None` for a non-200 response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_user_rank("url", {}, "u1")

    assert result is None


# ==========================================================
# fetch_user_streak -- this whole function (lines 86-94) had
# zero tests at all before this
# ==========================================================

from services.career_brain_service import fetch_user_streak


@pytest.mark.asyncio
async def test_fetch_user_streak_success(mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"current_streak": 4}]

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_user_streak("url", {}, "u1")

    assert result == {"current_streak": 4}


@pytest.mark.asyncio
async def test_fetch_user_streak_empty_data(mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_user_streak("url", {}, "u1")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_user_streak_non_200(mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = []

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("services.career_brain_service.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_user_streak("url", {}, "u1")

    assert result is None


# ==========================================================
# calculate_job_readiness_score: remaining branch gaps
# ==========================================================

def test_job_readiness_skill_gaps_as_dict():
    """Lines 191-194: skill_gaps can arrive as a dict of category -> list,
    not just a flat list."""
    analysis = {
        "skill_gaps": {
            "backend": ["Docker", "Kubernetes"],
            "cloud": ["AWS"]
        }
    }

    score = calculate_job_readiness_score(None, analysis, [], [])

    # base 50 + skill-gap-dict credit (25 - min(20, 3*3) = 16)
    # + analysis-completion bonus (10, awarded whenever analysis is truthy)
    # = 50 + 16 + 10 = 76
    assert score == 76


def test_job_readiness_mid_range_applications():
    """Line 202: the 5-9 applied applications band."""
    applications = [{"status": "applied"} for _ in range(6)]

    score = calculate_job_readiness_score(None, None, applications, [])

    # base 50 + 15 (5-9 band) = 65
    assert score == 65


def test_job_readiness_mid_range_interview_scores():
    """Lines 212-215: the 60-79 and 40-59 average interview score bands."""
    mid_high = calculate_job_readiness_score(
        None, None, [], [{"total_score": 65}]
    )
    # base 50 + 15 (60-79 band) = 65
    assert mid_high == 65

    mid_low = calculate_job_readiness_score(
        None, None, [], [{"total_score": 45}]
    )
    # base 50 + 10 (40-59 band) = 60
    assert mid_low == 60


# ==========================================================
# generate_behavioral_insights: remaining branch gaps
# ==========================================================

def test_behavioral_insights_low_rejection_ratio():
    """Lines 253-254: rejection ratio below 0.3 -> positive message."""
    applications = [
        {"status": "applied"},
        {"status": "applied"},
        {"status": "applied"},
        {"status": "applied"},
        {"status": "rejected"},
    ]

    insights = generate_behavioral_insights(applications, [], None, [])

    assert any("conversion rate" in i.lower() for i in insights)


def test_behavioral_insights_declining_scores():
    """Lines 261-262: latest interview score lower than the first."""
    interviews = [
        {"total_score": 80},
        {"total_score": 60},
        {"total_score": 40},
    ]

    insights = generate_behavioral_insights([], interviews, None, [])

    assert any("dropped" in i.lower() for i in insights)


def test_behavioral_insights_streak_zero():
    """Line 268: a streak object present but current_streak is 0."""
    streak = {"current_streak": 0}

    insights = generate_behavioral_insights([], [], streak, [])

    assert any("start your streak" in i.lower() for i in insights)


def test_behavioral_insights_saved_jobs_no_applications():
    """Line 274: 5+ saved jobs but fewer than 3 applications."""
    saved_jobs = [{}, {}, {}, {}, {}]
    applications = [{"status": "applied"}]

    insights = generate_behavioral_insights(applications, [], None, saved_jobs)

    assert any("haven't applied" in i.lower() for i in insights)


# ==========================================================
# detect_risks: exception-swallowing branches + last_practice_date path
# ==========================================================

def test_detect_risks_malformed_interview_date():
    """Lines 357-358: a created_at value that datetime.fromisoformat
    can't parse must be swallowed, not raised."""
    alerts = detect_risks(
        [],
        [{"created_at": "not-a-real-date"}],
        None,
        None
    )

    # Should not raise, and should not produce an interview-practice alert
    assert isinstance(alerts, list)
    assert not any("interview practice" in a.lower() for a in alerts)


def test_detect_risks_streak_last_practice_date_triggers_alert():
    """Lines 364-369: streak.last_practice_date parsed and stale (>7 days)."""
    old_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")

    alerts = detect_risks(
        [],
        [],
        {"current_streak": 5, "last_practice_date": old_date},
        None
    )

    assert any("no activity in" in a.lower() for a in alerts)


def test_detect_risks_streak_last_practice_date_malformed():
    """Line 370: a last_practice_date that strptime can't parse must be
    swallowed, not raised."""
    alerts = detect_risks(
        [],
        [],
        {"current_streak": 5, "last_practice_date": "not-a-date"},
        None
    )

    assert isinstance(alerts, list)
    assert not any("no activity in" in a.lower() for a in alerts)


# ==========================================================
# clear_cache: specific user_id branch
# ==========================================================

def test_clear_cache_specific_user(mocker):
    """Line 488: popping a single user's entry rather than wiping the
    whole cache."""
    import services.career_brain_service as cbs

    mocker.patch.object(
        cbs, "_career_brain_cache",
        {"u1": {"cached_at": 1}, "u2": {"cached_at": 2}}
    )

    clear_cache("u1")

    assert "u1" not in cbs._career_brain_cache
    assert "u2" in cbs._career_brain_cache