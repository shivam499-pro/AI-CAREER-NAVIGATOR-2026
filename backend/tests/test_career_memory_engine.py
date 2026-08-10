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


def test_calculate_trend_tie_with_nonpositive_first_score_returns_stable():
    """Covers the tie branch (increases == decreases) when first_score <= 0,
    where the ±5% check is skipped entirely (dividing by a zero/negative
    first_score would be nonsensical) and the code falls straight through
    to the trailing `return "stable"`.
    """
    # 0 -> 5 (increase), 5 -> 0 (decrease): tie, and first_score == 0
    assert engine._calculate_trend([0, 5, 0]) == "stable"


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
    """
    NOTE: the original version of this test configured each mock's
    select-chain with only ONE `.eq()` hop
    (`select.return_value.eq.return_value.execute...`), but the real code
    calls `.eq("user_id", ...).eq("career_path", ...)` -- TWO hops. That
    mismatch meant `existing_response`/`recent_response` were never
    actually returned; a fresh auto-generated MagicMock was returned
    instead, whose `.data` is truthy but `len(.data)` defaults to 0, so
    `if existing_response.data and len(existing_response.data) > 0` was
    always False. The test silently fell through to the CREATE branch
    while asserting on the UPDATE branch's name/intent -- which is exactly
    why lines 126-173 (the entire "update existing record" body) showed
    0% coverage despite this test existing and passing. Fixed below by
    chaining `.eq.return_value.eq.return_value` to match the real query,
    and by asserting on the actual computed values instead of just
    `result is True`.
    """
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
        {"total_score": 85},
    ]

    update_query = MagicMock()
    update_query.update.return_value.eq.return_value.execute.return_value = MagicMock()

    existing_query = MagicMock()
    existing_query.select.return_value.eq.return_value.eq.return_value.execute.return_value = existing_response

    recent_query = MagicMock()
    (
        recent_query.select.return_value
        .eq.return_value
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

    # Confirm the actual UPDATE branch ran (not a silent fallthrough to CREATE):
    # it must target the existing row by id, and it must never have called insert.
    update_query.update.assert_called_once()
    update_query.update.return_value.eq.assert_called_once_with("id", "memory-1")
    assert not hasattr(existing_query, "insert") or not existing_query.insert.called

    update_payload = update_query.update.call_args[0][0]
    # old_score=80 (session_count=2), new score=90 -> new_session_count=3
    # new_avg_score = int(((80*2) + 90) / 3) = int(250/3) = 83
    assert update_payload["session_count"] == 3
    assert update_payload["performance_score"] == 83
    # recent_scores = [70, 85, 90] -> strictly increasing -> "improving"
    assert update_payload["trend"] == "improving"
    # session_factor=min(0.3, 3*0.03)=0.09, stdev([70,85,90])~=10.41,
    # consistency_factor=max(0, 0.7 - 10.41/200)~=0.648 -> confidence ~= 0.74
    assert update_payload["confidence_score"] == pytest.approx(0.74, abs=0.01)
    assert "last_updated" in update_payload


# =============================================================================
# update_user_memory edge cases
# =============================================================================

def test_update_user_memory_updates_existing_record_with_no_prior_sessions(mocker):
    """When the interview_sessions lookup returns no rows (e.g. this is the
    first session ever recorded under this career_path even though a memory
    row already exists), recent_scores collapses to just the current score.
    This exercises the `else: score_variance = 0` branch, which the
    multi-session update test above can't reach.
    """
    existing_response = MagicMock()
    existing_response.data = [
        {"id": "memory-2", "performance_score": 60, "session_count": 1}
    ]

    recent_response = MagicMock()
    recent_response.data = []  # no prior interview_sessions rows

    update_query = MagicMock()
    update_query.update.return_value.eq.return_value.execute.return_value = MagicMock()

    existing_query = MagicMock()
    existing_query.select.return_value.eq.return_value.eq.return_value.execute.return_value = existing_response

    recent_query = MagicMock()
    (
        recent_query.select.return_value
        .eq.return_value
        .eq.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
    ) = recent_response

    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = [existing_query, recent_query, update_query]

    mocker.patch.object(engine, "_get_supabase", return_value=mock_supabase)

    result = engine.update_user_memory(
        "user1",
        {"career_path": "AI Engineer", "score": 90},
    )

    assert result is True
    update_payload = update_query.update.call_args[0][0]
    # recent_scores == [90] -> a single point -> trend defaults to "stable"
    assert update_payload["trend"] == "stable"
    # session_count 1 -> 2, avg = int(((60*1)+90)/2) = 75
    assert update_payload["session_count"] == 2
    assert update_payload["performance_score"] == 75


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

def test_update_user_memory_stdev_error_falls_back_to_zero_variance(mocker):
    """statistics.stdev can only raise StatisticsError for <2 data points,
    which the len(recent_scores) > 1 guard already prevents in practice --
    this test forces it anyway to exercise the defensive except branch."""
    import statistics

    existing_response = MagicMock()
    existing_response.data = [
        {"id": "memory-1", "performance_score": 80, "session_count": 2}
    ]

    recent_response = MagicMock()
    recent_response.data = [
        {"total_score": 70},
        {"total_score": 85},
    ]

    update_query = MagicMock()
    update_query.update.return_value.eq.return_value.execute.return_value = MagicMock()

    existing_query = MagicMock()
    existing_query.select.return_value.eq.return_value.eq.return_value.execute.return_value = existing_response

    recent_query = MagicMock()
    (
        recent_query.select.return_value
        .eq.return_value
        .eq.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
    ) = recent_response

    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = [existing_query, recent_query, update_query]

    mocker.patch.object(engine, "_get_supabase", return_value=mock_supabase)
    mocker.patch("statistics.stdev", side_effect=statistics.StatisticsError("mocked"))

    result = engine.update_user_memory(
        "user1", {"career_path": "AI Engineer", "score": 90}
    )

    assert result is True
    update_payload = update_query.update.call_args[0][0]
    # score_variance forced to 0 -> consistency_factor = 0.7
    # session_factor = min(0.3, 3*0.03) = 0.09 -> confidence = 0.79
    assert update_payload["confidence_score"] == pytest.approx(0.79, abs=0.01)