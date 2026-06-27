"""
Tests for services.recommendation_engine
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from services.recommendation_engine import (
    RecommendationEngine,
    recommendation_engine,
    get_job_recommendations,
    get_skill_recommendations,
    get_career_paths,
    get_learning_resources,
)


# =========================================================
# Fixtures
# =========================================================

@pytest.fixture
def engine():
    return RecommendationEngine()


# =========================================================
# Initialization
# =========================================================

def test_recommendation_engine_init_without_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    engine = RecommendationEngine()

    assert engine._supabase is None


@patch("services.recommendation_engine.create_client")
def test_recommendation_engine_init_with_env(
    mock_create_client,
    monkeypatch
):
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")

    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    engine = RecommendationEngine()

    assert engine._supabase == mock_client
    mock_create_client.assert_called_once()


# =========================================================
# recommend_jobs
# =========================================================

@pytest.mark.asyncio
async def test_recommend_jobs_happy_path(engine, mocker):
    jobs = [
        {
            "title": "Python Backend Engineer",
            "required_skills": ["python", "fastapi", "docker"],
            "experience_level": "mid"
        },
        {
            "title": "Frontend Engineer",
            "required_skills": ["react", "typescript"],
            "experience_level": "entry"
        },
        {
            "title": "DevOps Engineer",
            "required_skills": ["aws", "docker", "kubernetes"],
            "experience_level": "senior"
        }
    ]

    mocker.patch.object(
        engine,
        "_fetch_potential_jobs",
        AsyncMock(return_value=jobs)
    )

    result = await engine.recommend_jobs(
        user_id="user-1",
        skills=["Python", "Docker", "FastAPI"],
        experience_level="mid",
        limit=5
    )

    assert result["user_id"] == "user-1"
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0

    top = result["recommendations"][0]

    assert "job" in top
    assert "match_score" in top
    assert "matched_skills" in top
    assert "score" in top

    assert top["job"]["title"] == "Python Backend Engineer"


@pytest.mark.asyncio
async def test_recommend_jobs_sorted_by_score(engine, mocker):
    jobs = [
        {
            "title": "Low Match",
            "required_skills": ["java"],
            "experience_level": "entry"
        },
        {
            "title": "High Match",
            "required_skills": ["python", "docker"],
            "experience_level": "mid"
        }
    ]

    mocker.patch.object(
        engine,
        "_fetch_potential_jobs",
        AsyncMock(return_value=jobs)
    )

    result = await engine.recommend_jobs(
        user_id="user-1",
        skills=["python", "docker"],
        experience_level="mid"
    )

    recommendations = result["recommendations"]

    assert recommendations[0]["score"] >= recommendations[1]["score"]
    assert recommendations[0]["job"]["title"] == "High Match"


@pytest.mark.asyncio
async def test_recommend_jobs_empty_profile(engine, mocker):
    mocker.patch.object(
        engine,
        "_fetch_potential_jobs",
        AsyncMock(return_value=[])
    )

    result = await engine.recommend_jobs(
        user_id="user-1",
        skills=[],
        experience_level="entry"
    )

    assert result["recommendations"] == []
    assert result["total_found"] == 0


@pytest.mark.asyncio
async def test_recommend_jobs_limit(engine, mocker):
    jobs = []

    for i in range(20):
        jobs.append({
            "title": f"Job {i}",
            "required_skills": ["python"],
            "experience_level": "mid"
        })

    mocker.patch.object(
        engine,
        "_fetch_potential_jobs",
        AsyncMock(return_value=jobs)
    )

    result = await engine.recommend_jobs(
        user_id="user-1",
        skills=["python"],
        limit=5
    )

    assert len(result["recommendations"]) == 5


@pytest.mark.asyncio
async def test_recommend_jobs_ai_failure_fallback(engine, mocker):
    mocker.patch.object(
        engine,
        "_fetch_potential_jobs",
        side_effect=Exception("Database failure")
    )

    with pytest.raises(Exception):
        await engine.recommend_jobs(
            user_id="user-1",
            skills=["python"]
        )


# =========================================================
# recommend_skills_to_learn
# =========================================================

@pytest.mark.asyncio
async def test_recommend_skills_to_learn(engine, mocker):
    mock_market = MagicMock()

    mock_market.analyze_role_demand = AsyncMock(return_value={
        "high_demand_skills": ["docker", "kubernetes"],
        "growing_skills": ["terraform"]
    })

    mock_market.get_skill_trend = AsyncMock(return_value={
        "trend": "up"
    })

    mocker.patch(
        "services.market_analyzer.market_analyzer",
        mock_market
    )

    result = await engine.recommend_skills_to_learn(
        user_id="user-1",
        current_skills=["python"],
        target_role="DevOps Engineer"
    )

    assert result["target_role"] == "DevOps Engineer"
    assert len(result["recommendations"]) > 0
    assert "learning_path" in result


@pytest.mark.asyncio
async def test_recommend_skills_to_learn_empty(engine, mocker):
    mock_market = MagicMock()

    mock_market.analyze_role_demand = AsyncMock(return_value={
        "high_demand_skills": [],
        "growing_skills": []
    })

    mock_market.get_skill_trend = AsyncMock(return_value={
        "trend": "unknown"
    })

    mocker.patch(
        "services.market_analyzer.market_analyzer",
        mock_market
    )

    result = await engine.recommend_skills_to_learn(
        user_id="user-1",
        current_skills=[],
        target_role="Unknown"
    )

    assert result["recommendations"] == []


# =========================================================
# recommend_career_paths
# =========================================================

@pytest.mark.asyncio
async def test_recommend_career_paths(engine):
    result = await engine.recommend_career_paths(
        user_id="user-1",
        current_role="Software Engineer",
        skills=["python", "sql", "machine learning"],
        experience_years=3
    )

    assert result["current_role"] == "Software Engineer"
    assert "career_paths" in result
    assert len(result["career_paths"]) > 0
    assert result["recommended_path"] is not None


@pytest.mark.asyncio
async def test_recommend_career_paths_sorted(engine):
    result = await engine.recommend_career_paths(
        user_id="user-1",
        current_role="Engineer",
        skills=["python", "sql", "machine learning"],
        experience_years=2
    )

    paths = result["career_paths"]

    for i in range(len(paths) - 1):
        assert (
            paths[i]["match_score"]
            >= paths[i + 1]["match_score"]
        )


# =========================================================
# recommend_learning_resources
# =========================================================

@pytest.mark.asyncio
async def test_recommend_learning_resources_python(engine):
    result = await engine.recommend_learning_resources(
        "python",
        "beginner"
    )

    assert result["skill"] == "python"
    assert result["level"] == "beginner"
    assert len(result["resources"]) > 0


@pytest.mark.asyncio
async def test_recommend_learning_resources_unknown_skill(engine):
    result = await engine.recommend_learning_resources(
        "unknownskill"
    )

    assert result["resources"] == []


@pytest.mark.asyncio
async def test_recommend_learning_resources_invalid_level(engine):
    result = await engine.recommend_learning_resources(
        "python",
        "expert"
    )

    # Falls back to beginner
    assert len(result["resources"]) > 0


# =========================================================
# _check_experience_level
# =========================================================

def test_check_experience_level_match(engine):
    assert engine._check_experience_level(
        "mid",
        "senior"
    ) is True


def test_check_experience_level_no_match(engine):
    assert engine._check_experience_level(
        "senior",
        "entry"
    ) is False


def test_check_experience_level_missing(engine):
    assert engine._check_experience_level(
        None,
        "mid"
    ) is True


# =========================================================
# _fetch_potential_jobs
# =========================================================

@pytest.mark.asyncio
async def test_fetch_potential_jobs_default(engine):
    result = await engine._fetch_potential_jobs(
        location=None,
        remote_only=False,
        limit=10
    )

    assert result == []


# =========================================================
# Convenience wrappers
# =========================================================

@pytest.mark.asyncio
async def test_get_job_recommendations_wrapper(mocker):
    mocker.patch.object(
        recommendation_engine,
        "recommend_jobs",
        AsyncMock(return_value={"recommendations": []})
    )

    result = await get_job_recommendations(
        "user-1",
        ["python"]
    )

    assert "recommendations" in result


@pytest.mark.asyncio
async def test_get_skill_recommendations_wrapper(mocker):
    mocker.patch.object(
        recommendation_engine,
        "recommend_skills_to_learn",
        AsyncMock(return_value={"recommendations": []})
    )

    result = await get_skill_recommendations(
        "user-1",
        ["python"],
        "Backend Engineer"
    )

    assert "recommendations" in result


@pytest.mark.asyncio
async def test_get_career_paths_wrapper(mocker):
    mocker.patch.object(
        recommendation_engine,
        "recommend_career_paths",
        AsyncMock(return_value={"career_paths": []})
    )

    result = await get_career_paths(
        "user-1",
        "Engineer",
        ["python"],
        2
    )

    assert "career_paths" in result


@pytest.mark.asyncio
async def test_get_learning_resources_wrapper(mocker):
    mocker.patch.object(
        recommendation_engine,
        "recommend_learning_resources",
        AsyncMock(return_value={"resources": []})
    )

    result = await get_learning_resources("python")

    assert "resources" in result

