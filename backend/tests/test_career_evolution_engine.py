import time
from unittest.mock import MagicMock

import pytest

from services import career_evolution_engine as engine


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def clear_engine_cache():
    """Ensure test isolation."""
    engine.clear_cache()
    engine._supabase_client = None
    yield
    engine.clear_cache()
    engine._supabase_client = None


@pytest.fixture
def sample_memory_data():
    return [
        {
            "career_path": "AI Engineer",
            "performance_score": 80,
            "session_count": 5,
            "confidence_score": 0.85,
            "trend": "improving",
        },
        {
            "career_path": "Backend Engineer",
            "performance_score": 65,
            "session_count": 3,
            "confidence_score": 0.70,
            "trend": "stable",
        },
    ]


@pytest.fixture
def sample_session_data():
    return [
        {"career_path": "AI Engineer", "total_score": 70},
        {"career_path": "AI Engineer", "total_score": 80},
        {"career_path": "AI Engineer", "total_score": 90},
        {"career_path": "Backend Engineer", "total_score": 60},
        {"career_path": "Backend Engineer", "total_score": 65},
    ]


# =============================================================================
# CACHE TESTS
# =============================================================================

def test_cache_set_and_get():
    user_id = "user-1"
    data = {"test": True}

    engine._set_cached_evolution(user_id, data)

    result = engine._get_cached_evolution(user_id)

    assert result == data


def test_cache_expired_removes_entry():
    user_id = "user-expired"

    engine._evolution_cache[user_id] = (
        time.time() - (engine.EVOLUTION_CACHE_TTL + 10),
        {"old": True},
    )

    result = engine._get_cached_evolution(user_id)

    assert result is None
    assert user_id not in engine._evolution_cache


def test_clear_specific_cache():
    engine._set_cached_evolution("u1", {"a": 1})
    engine._set_cached_evolution("u2", {"b": 2})

    engine.clear_cache("u1")

    assert "u1" not in engine._evolution_cache
    assert "u2" in engine._evolution_cache


def test_clear_all_cache():
    engine._set_cached_evolution("u1", {"a": 1})
    engine._set_cached_evolution("u2", {"b": 2})

    engine.clear_cache()

    assert len(engine._evolution_cache) == 0


# =============================================================================
# VOLATILITY TESTS
# =============================================================================

def test_calculate_volatility_empty():
    assert engine._calculate_volatility([]) == 0.0


def test_calculate_volatility_single_value():
    assert engine._calculate_volatility([50]) == 0.0


def test_calculate_volatility_zero_mean():
    assert engine._calculate_volatility([0, 0]) == 0.0


def test_calculate_volatility_normal_case():
    result = engine._calculate_volatility([70, 80, 90])

    assert isinstance(result, float)
    assert 0 <= result <= 1


def test_calculate_volatility_clamped():
    result = engine._calculate_volatility([1, 1000])

    assert result <= 1.0


# =============================================================================
# GROWTH STATE TESTS
# =============================================================================

def test_growth_state_empty():
    assert engine._determine_growth_state([]) == "stagnating"


def test_growth_state_growing():
    paths = [
        {"trend": "improving"},
        {"trend": "improving"},
        {"trend": "stable"},
    ]

    assert engine._determine_growth_state(paths) == "growing"


def test_growth_state_declining():
    paths = [
        {"trend": "declining"},
        {"trend": "declining"},
        {"trend": "stable"},
    ]

    assert engine._determine_growth_state(paths) == "declining"


def test_growth_state_stagnating():
    paths = [
        {"trend": "improving"},
        {"trend": "declining"},
    ]

    assert engine._determine_growth_state(paths) == "stagnating"


# =============================================================================
# FALLBACK TESTS
# =============================================================================

def test_get_fallback_profile():
    result = engine._get_fallback_profile("user123")

    assert result == {
        "user_id": "user123",
        "career_paths": [],
        "overall_growth_state": "stagnating",
    }


# =============================================================================
# SUPABASE INITIALIZATION TESTS
# =============================================================================

def test_get_supabase_returns_none_when_not_configured(mocker):
    mocker.patch.object(engine, "supabase_url", None)
    mocker.patch.object(engine, "supabase_key", None)

    engine._supabase_client = None

    result = engine._get_supabase()

    assert result is None


def test_get_supabase_creates_client(mocker):
    mock_client = MagicMock()

    mocker.patch.object(engine, "supabase_url", "https://test.supabase.co")
    mocker.patch.object(engine, "supabase_key", "test-key")

    create_client_mock = mocker.patch.object(
        engine,
        "create_client",
        return_value=mock_client,
    )

    engine._supabase_client = None

    result = engine._get_supabase()

    assert result == mock_client
    create_client_mock.assert_called_once()


# =============================================================================
# EVOLUTION PROFILE TESTS
# =============================================================================

def test_get_user_profile_uses_cache(mocker):
    cached_profile = {
        "user_id": "cached-user",
        "career_paths": [],
        "overall_growth_state": "growing",
    }

    mocker.patch.object(
        engine,
        "_get_cached_evolution",
        return_value=cached_profile,
    )

    result = engine.get_user_evolution_profile("cached-user")

    assert result == cached_profile


def test_get_user_profile_fallback_when_no_supabase(mocker):
    mocker.patch.object(engine, "_get_cached_evolution", return_value=None)
    mocker.patch.object(engine, "_get_supabase", return_value=None)

    result = engine.get_user_evolution_profile("user1")

    assert result["user_id"] == "user1"
    assert result["career_paths"] == []
    assert result["overall_growth_state"] == "stagnating"


def test_get_user_profile_success(
    mocker,
    sample_memory_data,
    sample_session_data,
):
    memory_response = MagicMock()
    memory_response.data = sample_memory_data

    sessions_response = MagicMock()
    sessions_response.data = sample_session_data

    mock_supabase = MagicMock()

    first_query = MagicMock()
    first_query.select.return_value.eq.return_value.execute.return_value = memory_response
 
    second_query = MagicMock()
    second_query.select.return_value.eq.return_value.execute.return_value = sessions_response
    
    mock_supabase.table.side_effect = [
        first_query,
        second_query,
    ]

    mocker.patch.object(engine, "_get_cached_evolution", return_value=None)
    mocker.patch.object(engine, "_get_supabase", return_value=mock_supabase)

    cache_mock = mocker.patch.object(engine, "_set_cached_evolution")

    result = engine.get_user_evolution_profile("user123")

    assert result["user_id"] == "user123"
    assert len(result["career_paths"]) == 2
    assert "overall_growth_state" in result

    ai_path = result["career_paths"][0]

    assert "career_path" in ai_path
    assert "avg_score" in ai_path
    assert "trend" in ai_path
    assert "volatility" in ai_path
    assert "total_sessions" in ai_path
    assert "confidence" in ai_path

    cache_mock.assert_called_once()


def test_get_user_profile_handles_empty_responses(mocker):
    memory_response = MagicMock()
    memory_response.data = []

    sessions_response = MagicMock()
    sessions_response.data = []

    mock_supabase = MagicMock()

    first_query = MagicMock()
    first_query.eq.return_value.execute.return_value = memory_response

    second_query = MagicMock()
    second_query.eq.return_value.execute.return_value = sessions_response

    mock_supabase.table.side_effect = [
        first_query,
        second_query,
    ]

    mocker.patch.object(engine, "_get_cached_evolution", return_value=None)
    mocker.patch.object(engine, "_get_supabase", return_value=mock_supabase)

    result = engine.get_user_evolution_profile("user-empty")

    assert result["career_paths"] == []
    assert result["overall_growth_state"] == "stagnating"


def test_get_user_profile_exception_returns_fallback(mocker):
    mocker.patch.object(engine, "_get_cached_evolution", return_value=None)
    mocker.patch.object(
        engine,
        "_get_supabase",
        side_effect=Exception("database error"),
    )

    result = engine.get_user_evolution_profile("user-error")

    assert result["user_id"] == "user-error"
    assert result["career_paths"] == []
    assert result["overall_growth_state"] == "stagnating"


# =============================================================================
# UPDATE PROFILE TESTS
# =============================================================================

def test_update_profile_success():
    engine._set_cached_evolution("user1", {"data": True})

    result = engine.update_user_evolution_profile("user1")

    assert result is True
    assert "user1" not in engine._evolution_cache


def test_update_profile_user_not_in_cache():
    result = engine.update_user_evolution_profile("missing-user")

    assert result is True


def test_update_profile_exception(mocker):
    class BrokenDict(dict):
        def __contains__(self, key):
            raise RuntimeError("boom")

    mocker.patch.object(
        engine,
        "_evolution_cache",
        BrokenDict(),
    )

    result = engine.update_user_evolution_profile("user1")

    assert result is False