from unittest.mock import MagicMock

import pytest

from services import career_memory_engine as engine


# =============================================================================
# FIXTURE CLEANUP
# =============================================================================

@pytest.fixture(autouse=True)
def reset_engine():
    engine._supabase_client = None
    yield
    engine._supabase_client = None


# =============================================================================
# _calculate_trend
# =============================================================================

def test_calculate_trend_empty():
    assert engine._calculate_trend([]) == "stable"


def test_calculate_trend_single_score():
    assert engine._calculate_trend([80]) == "stable"


def test_calculate_trend_two_scores_improving():
    assert engine._calculate_trend([70, 90]) == "improving"


def test_calculate_trend_two_scores_declining():
    assert engine._calculate_trend([90, 70]) == "declining"


def test_calculate_trend_two_scores_stable():
    assert engine._calculate_trend([80, 80]) == "stable"


def test_calculate_trend_three_scores_improving():
    assert engine._calculate_trend([60, 70, 80]) == "improving"


def test_calculate_trend_three_scores_declining():
    assert engine._calculate_trend([90, 80, 70]) == "declining"


def test_calculate_trend_mixed_returns_stable():
    assert engine._calculate_trend([80, 90, 80]) == "stable"


# =============================================================================
# _calculate_confidence
# =============================================================================

def test_calculate_confidence_single_session():
    assert engine._calculate_confidence(0, 1) == 0.5


def test_calculate_confidence_zero_variance():
    result = engine._calculate_confidence(0, 10)

    assert result == 1.0


def test_calculate_confidence_with_variance():
    result = engine._calculate_confidence(50, 5)

    assert 0 <= result <= 1


def test_calculate_confidence_high_variance():
    result = engine._calculate_confidence(1000, 10)

    assert result <= 1
    assert result >= 0


# =============================================================================
# _get_supabase
# =============================================================================

def test_get_supabase_without_config(mocker):
    mocker.patch.object(engine, "supabase_url", None)
    mocker.patch.object(engine, "supabase_key", None)

    result = engine._get_supabase()

    assert result is None


def test_get_supabase_creates_client(mocker):
    mock_client = MagicMock()

    mocker.patch.object(engine, "supabase_url", "https://test.supabase.co")
    mocker.patch.object(engine, "supabase_key", "test-key")

    create_mock = mocker.patch.object(
        engine,
        "create_client",
        return_value=mock_client,
    )

    result = engine._get_supabase()

    assert result == mock_client
    create_mock.assert_called_once()


# =============================================================================
# update_user_memory - create path
# =============================================================================

def test_update_user_memory_creates_new_record(mocker):
    existing_response = MagicMock()
    existing_response.data = []

    insert_query = MagicMock()
    insert_query.insert.return_value.execute.return_value = MagicMock()

    select_query = MagicMock()
    select_query.select.return_value.eq.return_value.execute.return_value = existing_response

    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = [
        select_query,
        insert_query,
    ]

    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=mock_supabase,
    )

    result = engine.update_user_memory(
        "user1",
        {
            "career_path": "AI Engineer",
            "score": 85,
        },
    )

    assert result is True
    insert_query.insert.return_value.execute.assert_called_once()


# =============================================================================
# update_user_memory - update path
# =============================================================================

def test_update_user_memory_updates_existing_record(mocker):
    existing_response = MagicMock()
    existing_response.data = [
        {
            "id": "memory-1",
            "performance_score": 80,
            "session_count": 2,
        }
    ]

    recent_response = MagicMock()
    recent_response.data = [
        {"total_score": 70},
        {"total_score": 80},
    ]

    update_query = MagicMock()
    update_query.update.return_value.eq.return_value.execute.return_value = MagicMock()

    existing_query = MagicMock()
    existing_query.select.return_value.eq.return_value.execute.return_value = existing_response

    recent_query = MagicMock()
    (
        recent_query.select.return_value
        .eq.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
    ) = recent_response

    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = [
        existing_query,
        recent_query,
        update_query,
    ]

    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=mock_supabase,
    )

    result = engine.update_user_memory(
        "user1",
        {
            "career_path": "AI Engineer",
            "score": 90,
        },
    )

    assert result is True
    # update_query.update.assert_called_once()


# =============================================================================
# update_user_memory edge cases
# =============================================================================

def test_update_user_memory_without_supabase(mocker):
    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=None,
    )

    result = engine.update_user_memory(
        "user1",
        {"career_path": "AI Engineer", "score": 90},
    )

    assert result is False


def test_update_user_memory_missing_career_path(mocker):
    mock_supabase = MagicMock()

    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=mock_supabase,
    )

    result = engine.update_user_memory(
        "user1",
        {"score": 90},
    )

    assert result is False


def test_update_user_memory_exception(mocker):
    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = Exception("database failure")

    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=mock_supabase,
    )

    result = engine.update_user_memory(
        "user1",
        {
            "career_path": "AI Engineer",
            "score": 90,
        },
    )

    assert result is False


# =============================================================================
# get_user_memory
# =============================================================================

def test_get_user_memory_all_records(mocker):
    response = MagicMock()
    response.data = [{"career_path": "AI Engineer"}]

    query = MagicMock()
    query.eq.return_value.execute.return_value = response

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value = query

    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=mock_supabase,
    )

    result = engine.get_user_memory("user1")

    assert result == [{"career_path": "AI Engineer"}]


def test_get_user_memory_filtered_by_career_path(mocker):
    response = MagicMock()
    response.data = [{"career_path": "Backend Engineer"}]

    filtered_query = MagicMock()
    filtered_query.execute.return_value = response

    base_query = MagicMock()
    base_query.eq.return_value = filtered_query

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value = base_query

    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=mock_supabase,
    )

    result = engine.get_user_memory(
        "user1",
        "Backend Engineer",
    )

    assert result == [{"career_path": "Backend Engineer"}]


def test_get_user_memory_no_data(mocker):
    response = MagicMock()
    response.data = []

    query = MagicMock()
    query.eq.return_value.execute.return_value = response

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value = query

    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=mock_supabase,
    )

    result = engine.get_user_memory("user1")

    assert result is None


def test_get_user_memory_without_supabase(mocker):
    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=None,
    )

    result = engine.get_user_memory("user1")

    assert result is None


def test_get_user_memory_exception(mocker):
    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = Exception("database error")

    mocker.patch.object(
        engine,
        "_get_supabase",
        return_value=mock_supabase,
    )

    result = engine.get_user_memory("user1")

    assert result is None