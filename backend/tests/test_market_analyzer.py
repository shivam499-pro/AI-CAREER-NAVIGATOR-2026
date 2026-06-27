import pytest
from unittest.mock import MagicMock, patch

from services.market_analyzer import (
    MarketAnalyzer,
    SKILL_DEMAND,
    get_role_demand,
    get_trends,
    analyze_skill,
    get_personalized_advice,
)


# =========================================================
# Fixtures
# =========================================================

@pytest.fixture
def analyzer():
    return MarketAnalyzer()


# =========================================================
# Initialization Tests
# =========================================================

def test_market_analyzer_init_without_env(monkeypatch):
    """Should initialize with no supabase client if env vars missing."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    analyzer = MarketAnalyzer()

    assert analyzer._supabase is None


@patch("services.market_analyzer.create_client")
def test_market_analyzer_init_with_env(mock_create_client, monkeypatch):
    """Should initialize supabase client when env vars exist."""
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")

    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    analyzer = MarketAnalyzer()

    assert analyzer._supabase == mock_client
    mock_create_client.assert_called_once()


# =========================================================
# analyze_role_demand
# =========================================================

@pytest.mark.asyncio
async def test_analyze_role_demand_happy_path(analyzer):
    """Valid role should return expected schema."""
    result = await analyzer.analyze_role_demand("Backend Developer")

    assert result["role"] == "Backend Developer"
    assert result["category"] == "backend_developer"
    assert "high_demand_skills" in result
    assert "growing_skills" in result
    assert "stable_skills" in result
    assert isinstance(result["demand_score"], int)
    assert "analyzed_at" in result


@pytest.mark.asyncio
async def test_analyze_role_demand_unknown_role_defaults(analyzer):
    """Unknown roles should fallback to software_engineer."""
    result = await analyzer.analyze_role_demand("Astronaut Ninja")

    assert result["category"] == "software_engineer"
    assert result["demand_score"] == 50


@pytest.mark.asyncio
async def test_analyze_role_demand_empty_role(analyzer):
    """Empty role should not crash."""
    result = await analyzer.analyze_role_demand("")

    assert result["role"] == ""
    assert result["category"] == "software_engineer"


# =========================================================
# _calculate_demand_score
# =========================================================

def test_calculate_demand_score_high_priority(analyzer):
    score = analyzer._calculate_demand_score("Software Engineer")
    assert score == 100


def test_calculate_demand_score_mid_priority(analyzer):
    score = analyzer._calculate_demand_score("Data Scientist")
    assert score > 0


def test_calculate_demand_score_default(analyzer):
    score = analyzer._calculate_demand_score("Unknown Role")
    assert score == 50


# =========================================================
# get_market_trends
# =========================================================

@pytest.mark.asyncio
async def test_get_market_trends_happy_path(analyzer):
    result = await analyzer.get_market_trends("30d")

    assert result["timeframe"] == "30d"
    assert "top_growing_skills" in result
    assert "declining_skills" in result
    assert "salary_trends" in result
    assert "remote_opportunity" in result
    assert "updated_at" in result


@pytest.mark.asyncio
async def test_get_market_trends_invalid_timeframe(analyzer):
    """
    Invalid timeframe should raise ValueError
    because int() conversion fails.
    """
    with pytest.raises(ValueError):
        await analyzer.get_market_trends("invalid")


# =========================================================
# get_skill_trend
# =========================================================

@pytest.mark.asyncio
async def test_get_skill_trend_high_demand(analyzer):
    result = await analyzer.get_skill_trend("python")

    assert result["demand"] == "high"
    assert result["trend"] == "growing"
    assert result["score"] == 85


@pytest.mark.asyncio
async def test_get_skill_trend_growing(analyzer):
    result = await analyzer.get_skill_trend("rust")

    assert result["demand"] == "growing"
    assert result["trend"] == "up"


@pytest.mark.asyncio
async def test_get_skill_trend_stable(analyzer):
    result = await analyzer.get_skill_trend("java")

    assert result["demand"] == "stable"
    assert result["trend"] == "flat"


@pytest.mark.asyncio
async def test_get_skill_trend_unknown(analyzer):
    result = await analyzer.get_skill_trend("ancient-cobol-ai")

    assert result["demand"] == "unknown"
    assert result["score"] == 30


@pytest.mark.asyncio
async def test_get_skill_trend_empty(analyzer):
    result = await analyzer.get_skill_trend("")

    assert result["demand"] == "unknown"


# =========================================================
# compare_roles
# =========================================================

@pytest.mark.asyncio
async def test_compare_roles_happy_path(analyzer):
    roles = ["Backend Developer", "Frontend Developer"]

    result = await analyzer.compare_roles(roles)

    assert "roles" in result
    assert len(result["roles"]) == 2
    assert result["highest_demand"] is not None
    assert "compared_at" in result


@pytest.mark.asyncio
async def test_compare_roles_empty_list(analyzer):
    result = await analyzer.compare_roles([])

    assert result["roles"] == []
    assert result["highest_demand"] is None


# =========================================================
# get_career_advice
# =========================================================

@pytest.mark.asyncio
async def test_get_career_advice_high_match(analyzer):
    skills = ["python", "docker", "postgresql"]

    result = await analyzer.get_career_advice(
        skills,
        "Backend Developer"
    )

    assert result["target_role"] == "Backend Developer"
    assert result["skill_match_percentage"] > 0
    assert isinstance(result["matching_skills"], list)
    assert isinstance(result["skills_to_develop"], list)
    assert "advice" in result


@pytest.mark.asyncio
async def test_get_career_advice_no_skills(analyzer):
    result = await analyzer.get_career_advice(
        [],
        "Backend Developer"
    )

    assert result["skill_match_percentage"] == 0
    assert len(result["matching_skills"]) == 0


@pytest.mark.asyncio
async def test_get_career_advice_null_like_values(analyzer):
    """
    Simulate edge-case empty strings in skills.
    """
    result = await analyzer.get_career_advice(
        ["", "python", " "],
        "Backend Developer"
    )

    assert "skill_match_percentage" in result


# =========================================================
# _generate_advice
# =========================================================

def test_generate_advice_high_match(analyzer):
    role_analysis = {"role": "Backend Developer"}

    advice = analyzer._generate_advice(role_analysis, 80)

    assert "strong skills" in advice.lower()


def test_generate_advice_medium_match(analyzer):
    role_analysis = {"role": "Backend Developer"}

    advice = analyzer._generate_advice(role_analysis, 50)

    assert "good fit" in advice.lower()


def test_generate_advice_low_match(analyzer):
    role_analysis = {
        "role": "Backend Developer",
        "high_demand_skills": ["python", "docker", "postgresql"]
    }

    advice = analyzer._generate_advice(role_analysis, 10)

    assert "consider learning" in advice.lower()


# =========================================================
# Convenience Functions
# =========================================================

@pytest.mark.asyncio
async def test_get_role_demand_wrapper():
    result = await get_role_demand("Backend Developer")

    assert result["role"] == "Backend Developer"


@pytest.mark.asyncio
async def test_get_trends_wrapper():
    result = await get_trends("30d")

    assert result["timeframe"] == "30d"


@pytest.mark.asyncio
async def test_analyze_skill_wrapper():
    result = await analyze_skill("python")

    assert result["skill"] == "python"


@pytest.mark.asyncio
async def test_get_personalized_advice_wrapper():
    result = await get_personalized_advice(
        ["python"],
        "Backend Developer"
    )

    assert result["target_role"] == "Backend Developer"


# =========================================================
# Error Handling / Graceful Failure
# =========================================================
@pytest.mark.asyncio
async def test_compare_roles_analysis_failure(analyzer, mocker):
    """
    Simulate internal analysis failure and verify graceful fallback.
    """

    mocker.patch.object(
        analyzer,
        "analyze_role_demand",
        side_effect=Exception("AI failure")
    )

    result = await analyzer.compare_roles(["Backend Developer"])

    assert result["roles"] == []
    assert result["highest_demand"] is None
    assert "error" in result


@pytest.mark.asyncio
async def test_get_career_advice_analysis_failure(analyzer, mocker):
    """
    Simulate upstream analysis failure.
    """

    mocker.patch.object(
        analyzer,
        "analyze_role_demand",
        side_effect=Exception("Service unavailable")
    )

    with pytest.raises(Exception):
        await analyzer.get_career_advice(
            ["python"],
            "Backend Developer"
        )


# =========================================================
# Data Integrity
# =========================================================

def test_skill_demand_structure():
    """Validate static SKILL_DEMAND structure."""

    assert isinstance(SKILL_DEMAND, dict)

    for category, data in SKILL_DEMAND.items():
        assert "high_demand" in data
        assert "growing" in data
        assert "stable" in data

        assert isinstance(data["high_demand"], list)
        assert isinstance(data["growing"], list)
        assert isinstance(data["stable"], list)

