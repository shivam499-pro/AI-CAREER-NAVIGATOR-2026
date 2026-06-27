import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.badges import router, VALID_EVENTS
from core.middleware import get_current_user, AuthenticatedUser
from services.badge_service import (
    check_and_award_badges,
    check_badges_on_session_complete,
    BADGES,
)


# ─── Test App Setup ───────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router, prefix="/api/v1/badges")


def make_mock_user(user_id: str = "test-user-123") -> AuthenticatedUser:
    """Return a real AuthenticatedUser — FastAPI type-checks dependencies."""
    return AuthenticatedUser(user_id=user_id, email="test@test.com", role="user")


def override_auth(user_id: str = "test-user-123"):
    """
    Returns a dependency override function for get_current_user.
    FastAPI resolves Depends() through its DI system — patching the import
    has no effect. dependency_overrides replaces the dependency at the app level.
    """
    def _override():
        return make_mock_user(user_id)
    return _override


# ─── 1. BADGES dict (service) ─────────────────────────────────────────────────

def test_badges_dict_has_all_12_entries():
    assert len(BADGES) == 12


def test_badges_dict_all_entries_have_required_fields():
    required = {"id", "name", "emoji", "description", "xp_reward", "rarity"}
    for badge_id, badge in BADGES.items():
        missing = required - badge.keys()
        assert not missing, f"Badge '{badge_id}' missing fields: {missing}"


def test_badges_dict_key_matches_id_field():
    # Dict key and badge["id"] must always match — router depends on this
    for key, badge in BADGES.items():
        assert key == badge["id"], f"Key '{key}' does not match id '{badge['id']}'"


# ─── 2. VALID_EVENTS (router) ─────────────────────────────────────────────────

def test_valid_events_contains_all_expected():
    expected = {
        "session_complete", "perfect_score", "hard_mode",
        "simulation", "voice_used", "challenge_created",
        "challenge_won", "streak_milestone",
    }
    assert expected == VALID_EVENTS


# ─── 3. check_and_award_badges (service) ─────────────────────────────────────

def test_check_and_award_badges_returns_expected_schema():
    with patch("services.badge_service.get_user_earned_badges") as mock_earned, \
         patch("services.badge_service.get_user_streak_data") as mock_streak, \
         patch("services.badge_service.get_user_rank_data") as mock_rank, \
         patch("services.badge_service.get_challenges_created_count") as mock_challenges, \
         patch("services.badge_service.award_badge") as mock_award, \
         patch("services.badge_service.add_xp_to_user") as mock_xp:

        mock_earned.return_value = set()
        mock_streak.return_value = {"current_streak": 0, "total_sessions": 1}
        mock_rank.return_value = {"xp": 0, "level": 1}
        mock_challenges.return_value = 0
        mock_award.return_value = BADGES["first_session"]
        mock_xp.return_value = {"xp": 10, "level": 1, "xp_earned": 10}

        result = check_and_award_badges("test-user-123", "session_complete")

        assert "new_badges" in result
        assert "total_xp_earned" in result
        assert "rank_update" in result


def test_check_and_award_badges_awards_first_session():
    with patch("services.badge_service.get_user_earned_badges") as mock_earned, \
         patch("services.badge_service.get_user_streak_data") as mock_streak, \
         patch("services.badge_service.get_user_rank_data") as mock_rank, \
         patch("services.badge_service.get_challenges_created_count") as mock_challenges, \
         patch("services.badge_service.award_badge") as mock_award, \
         patch("services.badge_service.add_xp_to_user") as mock_xp:

        mock_earned.return_value = set()
        mock_streak.return_value = {"current_streak": 0, "total_sessions": 1}
        mock_rank.return_value = {"xp": 0, "level": 1}
        mock_challenges.return_value = 0
        mock_award.return_value = BADGES["first_session"]
        mock_xp.return_value = {"xp": 10, "level": 1, "xp_earned": 10}

        result = check_and_award_badges("test-user-123", "session_complete")

        mock_award.assert_called_with("test-user-123", "first_session")
        assert result["total_xp_earned"] == BADGES["first_session"]["xp_reward"]


def test_check_and_award_badges_skips_already_earned():
    with patch("services.badge_service.get_user_earned_badges") as mock_earned, \
         patch("services.badge_service.get_user_streak_data") as mock_streak, \
         patch("services.badge_service.get_user_rank_data") as mock_rank, \
         patch("services.badge_service.get_challenges_created_count") as mock_challenges, \
         patch("services.badge_service.award_badge") as mock_award, \
         patch("services.badge_service.add_xp_to_user"):

        # User already has first_session
        mock_earned.return_value = {"first_session"}
        mock_streak.return_value = {"current_streak": 0, "total_sessions": 5}
        mock_rank.return_value = {"xp": 10, "level": 1}
        mock_challenges.return_value = 0
        mock_award.return_value = None

        check_and_award_badges("test-user-123", "session_complete")

        # award_badge should NOT be called for first_session
        for call in mock_award.call_args_list:
            assert call[0][1] != "first_session"


def test_check_and_award_badges_unknown_event_returns_empty():
    with patch("services.badge_service.get_user_earned_badges") as mock_earned, \
         patch("services.badge_service.get_user_streak_data") as mock_streak, \
         patch("services.badge_service.get_user_rank_data") as mock_rank, \
         patch("services.badge_service.get_challenges_created_count") as mock_challenges:

        mock_earned.return_value = set()
        mock_streak.return_value = {"current_streak": 0, "total_sessions": 0}
        mock_rank.return_value = {"xp": 0, "level": 1}
        mock_challenges.return_value = 0

        result = check_and_award_badges("test-user-123", "nonexistent_event")

        assert result["new_badges"] == []
        assert result["total_xp_earned"] == 0


# ─── 4. check_badges_on_session_complete (service) ───────────────────────────

def test_session_complete_fires_all_applicable_events():
    """
    Fix #7 — verify all event branches actually fire.
    Before the fix, hard_mode/simulation/voice_used were silently skipped.
    """
    with patch("services.badge_service.check_and_award_badges") as mock_check:
        mock_check.return_value = {
            "new_badges": [],
            "total_xp_earned": 0,
            "rank_update": None
        }

        check_badges_on_session_complete(
            user_id="test-user-123",
            total_score=50,
            difficulty="hard",
            is_simulation=True,
            is_voice=True
        )

        fired_events = [call[0][1] for call in mock_check.call_args_list]

        assert "session_complete" in fired_events
        assert "perfect_score" in fired_events
        assert "hard_mode" in fired_events
        assert "simulation" in fired_events
        assert "voice_used" in fired_events


def test_session_complete_only_fires_session_when_no_extras():
    with patch("services.badge_service.check_and_award_badges") as mock_check:
        mock_check.return_value = {
            "new_badges": [],
            "total_xp_earned": 0,
            "rank_update": None
        }

        check_badges_on_session_complete(user_id="test-user-123")

        fired_events = [call[0][1] for call in mock_check.call_args_list]

        assert fired_events == ["session_complete"]


def test_session_complete_merges_xp_across_events():
    with patch("services.badge_service.check_and_award_badges") as mock_check:
        mock_check.return_value = {
            "new_badges": [BADGES["first_session"]],
            "total_xp_earned": 10,
            "rank_update": {"xp": 10, "level": 1}
        }

        result = check_badges_on_session_complete(
            user_id="test-user-123",
            total_score=50,
            difficulty="hard",
        )

        # 3 events fired (session_complete + perfect_score + hard_mode)
        # each returning 10 XP → total should be 30
        assert result["total_xp_earned"] == 30
        assert len(result["new_badges"]) == 3


# ─── 5. Router — GET /{user_id} ───────────────────────────────────────────────

def test_get_badges_forbidden_for_wrong_user():
    app.dependency_overrides[get_current_user] = override_auth("user-A")

    try:
        client = TestClient(app)
        response = client.get("/api/v1/badges/user-B")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_get_badges_returns_correct_shape():
    app.dependency_overrides[get_current_user] = override_auth("test-user-123")

    mock_count = MagicMock()
    mock_count.count = 1

    mock_data = MagicMock()
    mock_data.data = [{"badge_id": "first_session", "earned_at": "2026-01-01T00:00:00"}]

    try:
        with patch("routers.badges.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value \
                .eq.return_value.execute.return_value = mock_count

            mock_supabase.table.return_value.select.return_value \
                .eq.return_value.range.return_value.execute.return_value = mock_data

            client = TestClient(app)
            response = client.get("/api/v1/badges/test-user-123")

        assert response.status_code == 200
        body = response.json()
        assert "earned" in body
        assert "all_badges" in body
        assert "pagination" in body
        assert len(body["all_badges"]) == 12
    finally:
        app.dependency_overrides.clear()


# ─── 6. Router — POST /check ──────────────────────────────────────────────────

def test_check_endpoint_rejects_invalid_event():
    app.dependency_overrides[get_current_user] = override_auth("test-user-123")

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/badges/check",
            json={"user_id": "test-user-123", "event": "not_a_real_event"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_check_endpoint_forbidden_for_wrong_user():
    app.dependency_overrides[get_current_user] = override_auth("user-A")

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/badges/check",
            json={"user_id": "user-B", "event": "session_complete"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_check_endpoint_returns_newly_earned():
    app.dependency_overrides[get_current_user] = override_auth("test-user-123")

    try:
        with patch("routers.badges.check_and_award_badges") as mock_service:
            mock_service.return_value = {
                "new_badges": [BADGES["first_session"]],
                "total_xp_earned": 10,
                "rank_update": None
            }

            client = TestClient(app)
            response = client.post(
                "/api/v1/badges/check",
                json={"user_id": "test-user-123", "event": "session_complete"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "newly_earned" in body
        assert len(body["newly_earned"]) == 1
        assert body["newly_earned"][0]["id"] == "first_session"
    finally:
        app.dependency_overrides.clear()