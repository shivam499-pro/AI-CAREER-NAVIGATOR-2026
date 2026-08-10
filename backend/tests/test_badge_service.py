"""
Tests for services/badge_service.py.

tests/test_badges.py already covers routers/badges.py end-to-end (through
HTTP), which exercises some of this service indirectly. This file unit-
tests badge_service.py's own functions directly and exhaustively: each
small Supabase-backed helper, the pure calculate_level/calculate_title
functions, and every branch of check_and_award_badges and
check_badges_on_session_complete.
"""
import pytest
from unittest.mock import MagicMock, patch

from services.badge_service import (
    BADGES,
    get_user_earned_badges,
    get_user_streak_data,
    get_user_rank_data,
    get_challenges_created_count,
    award_badge,
    add_xp_to_user,
    calculate_level,
    calculate_title,
    check_and_award_badges,
    check_badges_on_session_complete,
    _merge,
)


def make_execute_result(data):
    result = MagicMock()
    result.data = data
    return result


def build_chain(execute_result):
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.update.return_value = chain
    chain.insert.return_value = chain
    chain.execute.return_value = execute_result
    return chain


# =============================================================================
# get_user_earned_badges
# =============================================================================

class TestGetUserEarnedBadges:
    def test_returns_set_of_badge_ids(self):
        chain = build_chain(make_execute_result([{"badge_id": "first_session"}, {"badge_id": "streak_7"}]))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            result = get_user_earned_badges("u1")
        assert result == {"first_session", "streak_7"}

    def test_no_data_returns_empty_set(self):
        chain = build_chain(make_execute_result([]))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            result = get_user_earned_badges("u1")
        assert result == set()

    def test_exception_returns_empty_set(self):
        with patch("services.badge_service.get_supabase", side_effect=RuntimeError("db down")):
            result = get_user_earned_badges("u1")
        assert result == set()


# =============================================================================
# get_user_streak_data
# =============================================================================

class TestGetUserStreakData:
    def test_returns_first_record(self):
        chain = build_chain(make_execute_result([{"current_streak": 5, "longest_streak": 10, "total_sessions": 20}]))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            result = get_user_streak_data("u1")
        assert result["current_streak"] == 5

    def test_no_data_returns_default(self):
        chain = build_chain(make_execute_result([]))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            result = get_user_streak_data("u1")
        assert result == {"current_streak": 0, "longest_streak": 0, "total_sessions": 0}

    def test_exception_returns_default(self):
        with patch("services.badge_service.get_supabase", side_effect=RuntimeError("db down")):
            result = get_user_streak_data("u1")
        assert result == {"current_streak": 0, "longest_streak": 0, "total_sessions": 0}


# =============================================================================
# get_user_rank_data
# =============================================================================

class TestGetUserRankData:
    def test_returns_first_record(self):
        chain = build_chain(make_execute_result([{"xp": 300, "level": 3}]))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            result = get_user_rank_data("u1")
        assert result == {"xp": 300, "level": 3}

    def test_no_data_returns_default(self):
        chain = build_chain(make_execute_result([]))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            result = get_user_rank_data("u1")
        assert result == {"xp": 0, "level": 1}

    def test_exception_returns_default(self):
        with patch("services.badge_service.get_supabase", side_effect=RuntimeError("db down")):
            result = get_user_rank_data("u1")
        assert result == {"xp": 0, "level": 1}


# =============================================================================
# get_challenges_created_count
# =============================================================================

class TestGetChallengesCreatedCount:
    def test_counts_rows(self):
        chain = build_chain(make_execute_result([{"id": 1}, {"id": 2}, {"id": 3}]))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            assert get_challenges_created_count("u1") == 3

    def test_no_data_returns_zero(self):
        chain = build_chain(make_execute_result(None))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            assert get_challenges_created_count("u1") == 0

    def test_exception_returns_zero(self):
        with patch("services.badge_service.get_supabase", side_effect=RuntimeError("db down")):
            assert get_challenges_created_count("u1") == 0


# =============================================================================
# award_badge
# =============================================================================

class TestAwardBadge:
    def test_success_returns_badge_info(self):
        chain = build_chain(make_execute_result(None))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            result = award_badge("u1", "first_session")
        assert result == BADGES["first_session"]

    def test_unknown_badge_id_returns_none_even_on_success(self):
        chain = build_chain(make_execute_result(None))
        with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
            result = award_badge("u1", "not_a_real_badge")
        assert result is None

    def test_duplicate_constraint_error_returns_none_quietly(self):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )
        with patch("services.badge_service.get_supabase", return_value=mock_supabase):
            result = award_badge("u1", "first_session")
        assert result is None

    def test_unrelated_error_logs_and_returns_none(self, caplog):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
            "connection reset"
        )
        with patch("services.badge_service.get_supabase", return_value=mock_supabase):
            with caplog.at_level("ERROR"):
                result = award_badge("u1", "first_session")
        assert result is None
        assert any("Error awarding badge" in r.message for r in caplog.records)


# =============================================================================
# add_xp_to_user
# =============================================================================

class TestAddXpToUser:
    def test_existing_xp_updates_record(self):
        with patch(
            "services.badge_service.get_user_rank_data",
            return_value={"xp": 90, "level": 1},
        ):
            chain = build_chain(make_execute_result(None))
            with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
                result = add_xp_to_user("u1", 50)

        assert result["xp"] == 140
        assert result["level"] == 2
        assert result["xp_earned"] == 50
        chain.update.assert_called_once()

    def test_no_prior_xp_inserts_new_record(self):
        with patch(
            "services.badge_service.get_user_rank_data",
            return_value={"xp": 0, "level": 1},
        ):
            chain = build_chain(make_execute_result(None))
            with patch("services.badge_service.get_supabase", return_value=MagicMock(table=lambda *_: chain)):
                result = add_xp_to_user("u1", 30)

        assert result["xp"] == 30
        chain.insert.assert_called_once()
        chain.update.assert_not_called()

    def test_exception_returns_safe_default(self):
        with patch(
            "services.badge_service.get_user_rank_data",
            side_effect=RuntimeError("db down"),
        ):
            result = add_xp_to_user("u1", 30)

        assert result == {"xp": 0, "level": 1, "xp_earned": 0}


# =============================================================================
# calculate_level / calculate_title
# =============================================================================

class TestCalculateLevel:
    @pytest.mark.parametrize(
        "xp,expected_level",
        [
            (0, 1), (99, 1),
            (100, 2), (249, 2),
            (250, 3), (499, 3),
            (500, 4), (899, 4),
            (900, 5), (1399, 5),
            (1400, 6), (1999, 6),
            (2000, 7), (9999, 7),
        ],
    )
    def test_boundaries(self, xp, expected_level):
        assert calculate_level(xp) == expected_level


class TestCalculateTitle:
    @pytest.mark.parametrize(
        "level,expected_title",
        [(1, "🌱 Fresher"), (2, "📚 Beginner"), (3, "💼 Junior"), (4, "⚡ Mid-level"),
         (5, "🚀 Senior"), (6, "👑 Principal"), (7, "🏆 Legend")],
    )
    def test_known_levels(self, level, expected_title):
        assert calculate_title(level) == expected_title

    def test_unknown_level_falls_back_to_fresher(self):
        assert calculate_title(99) == "🌱 Fresher"


# =============================================================================
# check_and_award_badges
# =============================================================================

def patch_state(earned=None, streak=None, rank=None, challenges=0):
    """Patch all the data-gathering helpers check_and_award_badges relies on."""
    return (
        patch("services.badge_service.get_user_earned_badges", return_value=earned or set()),
        patch(
            "services.badge_service.get_user_streak_data",
            return_value=streak or {"current_streak": 0, "longest_streak": 0, "total_sessions": 0},
        ),
        patch(
            "services.badge_service.get_user_rank_data",
            return_value=rank or {"xp": 0, "level": 1},
        ),
        patch("services.badge_service.get_challenges_created_count", return_value=challenges),
    )


class TestCheckAndAwardBadgesSessionComplete:
    def test_first_session_badge_condition_is_always_true(self):
        """
        DOCUMENTS A REAL FINDING: the "first_session" check is
        `if "first_session" not in earned_badges and total_sessions >= 0`.
        Since total_sessions can never be negative, `>= 0` is always
        true — this badge fires on ANY session_complete event as long as
        it hasn't been awarded yet, even if total_sessions is 0 (i.e.
        the streak record hasn't even incremented yet for this session).
        It isn't gated on "at least 1 session" the way sessions_10/50 are.
        """
        p1, p2, p3, p4 = patch_state(streak={"current_streak": 0, "longest_streak": 0, "total_sessions": 0})
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 10, "level": 1}):
            result = check_and_award_badges("u1", "session_complete")

        badge_ids = [b["id"] for b in result["new_badges"]]
        assert "first_session" in badge_ids

    def test_sessions_10_and_50_thresholds(self):
        p1, p2, p3, p4 = patch_state(streak={"current_streak": 0, "longest_streak": 0, "total_sessions": 50})
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 10, "level": 1}):
            result = check_and_award_badges("u1", "session_complete")

        badge_ids = {b["id"] for b in result["new_badges"]}
        assert {"first_session", "sessions_10", "sessions_50"}.issubset(badge_ids)

    def test_already_earned_badges_are_not_reawarded(self):
        p1, p2, p3, p4 = patch_state(
            earned={"first_session", "sessions_10", "sessions_50"},
            streak={"current_streak": 0, "longest_streak": 0, "total_sessions": 50},
        )
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge") as mock_award:
            result = check_and_award_badges("u1", "session_complete")

        mock_award.assert_not_called()
        assert result["new_badges"] == []
        assert result["total_xp_earned"] == 0

    def test_streak_badges_fire_on_session_complete(self):
        p1, p2, p3, p4 = patch_state(streak={"current_streak": 30, "longest_streak": 30, "total_sessions": 5})
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 10, "level": 1}):
            result = check_and_award_badges("u1", "session_complete")

        badge_ids = {b["id"] for b in result["new_badges"]}
        assert {"streak_7", "streak_30"}.issubset(badge_ids)


class TestCheckAndAwardBadgesOtherEvents:
    def test_perfect_score_event(self):
        p1, p2, p3, p4 = patch_state()
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 10, "level": 1}):
            result = check_and_award_badges("u1", "perfect_score")

        assert [b["id"] for b in result["new_badges"]] == ["perfect_score"]

    def test_hard_mode_event(self):
        p1, p2, p3, p4 = patch_state()
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 10, "level": 1}):
            result = check_and_award_badges("u1", "hard_mode")

        assert [b["id"] for b in result["new_badges"]] == ["hard_mode"]

    def test_simulation_event(self):
        p1, p2, p3, p4 = patch_state()
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 10, "level": 1}):
            result = check_and_award_badges("u1", "simulation")

        assert [b["id"] for b in result["new_badges"]] == ["simulation"]

    def test_voice_used_event(self):
        p1, p2, p3, p4 = patch_state()
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 10, "level": 1}):
            result = check_and_award_badges("u1", "voice_used")

        assert [b["id"] for b in result["new_badges"]] == ["voice_user"]

    def test_challenge_created_requires_at_least_one_challenge(self):
        p1, p2, p3, p4 = patch_state(challenges=0)
        with p1, p2, p3, p4, patch("services.badge_service.award_badge") as mock_award:
            result = check_and_award_badges("u1", "challenge_created")

        mock_award.assert_not_called()
        assert result["new_badges"] == []

    def test_challenge_created_with_a_challenge_awards_challenger(self):
        p1, p2, p3, p4 = patch_state(challenges=1)
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 10, "level": 1}):
            result = check_and_award_badges("u1", "challenge_created")

        assert [b["id"] for b in result["new_badges"]] == ["challenger"]

    def test_challenge_won_rank_1_awards_weekly_winner(self):
        p1, p2, p3, p4 = patch_state()
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 200, "level": 1}):
            result = check_and_award_badges("u1", "challenge_won", event_data={"rank": 1})

        assert [b["id"] for b in result["new_badges"]] == ["weekly_winner"]

    def test_challenge_won_rank_2_awards_nothing(self):
        p1, p2, p3, p4 = patch_state()
        with p1, p2, p3, p4, patch("services.badge_service.award_badge") as mock_award:
            result = check_and_award_badges("u1", "challenge_won", event_data={"rank": 2})

        mock_award.assert_not_called()

    def test_challenge_won_without_event_data_awards_nothing(self):
        p1, p2, p3, p4 = patch_state()
        with p1, p2, p3, p4, patch("services.badge_service.award_badge") as mock_award:
            result = check_and_award_badges("u1", "challenge_won", event_data=None)

        mock_award.assert_not_called()

    def test_streak_milestone_event_checks_streak_badges(self):
        p1, p2, p3, p4 = patch_state(streak={"current_streak": 7, "longest_streak": 7, "total_sessions": 3})
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 50, "level": 1}):
            result = check_and_award_badges("u1", "streak_milestone")

        assert [b["id"] for b in result["new_badges"]] == ["streak_7"]

    def test_level_5_check_applies_regardless_of_event_type(self):
        """
        DOCUMENTS ACTUAL BEHAVIOR: the level_5 check is NOT gated inside
        an `if event == ...` block, so it's evaluated on every call
        regardless of which event triggered the check.
        """
        p1, p2, p3, p4 = patch_state(rank={"xp": 900, "level": 5})
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 100, "level": 5}):
            result = check_and_award_badges("u1", "perfect_score")

        badge_ids = {b["id"] for b in result["new_badges"]}
        assert {"perfect_score", "level_5"}.issubset(badge_ids)

    def test_unrecognized_event_only_checks_level_5(self):
        p1, p2, p3, p4 = patch_state(rank={"xp": 900, "level": 5})
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)), \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 100, "level": 5}):
            result = check_and_award_badges("u1", "some_unknown_event")

        assert [b["id"] for b in result["new_badges"]] == ["level_5"]


class TestCheckAndAwardBadgesAggregation:
    def test_total_xp_sums_across_multiple_new_badges(self):
        p1, p2, p3, p4 = patch_state(streak={"current_streak": 0, "longest_streak": 0, "total_sessions": 10})
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", side_effect=lambda uid, bid: BADGES.get(bid)) as mock_award, \
             patch("services.badge_service.add_xp_to_user", return_value={"xp": 999, "level": 2}) as mock_xp:
            result = check_and_award_badges("u1", "session_complete")

        # first_session (10) + sessions_10 (25) = 35
        assert result["total_xp_earned"] == 35
        mock_xp.assert_called_once_with("u1", 35)
        assert result["rank_update"] == {"xp": 999, "level": 2}

    def test_no_badges_awarded_skips_xp_call_entirely(self):
        p1, p2, p3, p4 = patch_state(
            earned={"first_session", "sessions_10", "sessions_50", "streak_7", "streak_30", "level_5"}
        )
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge") as mock_award, \
             patch("services.badge_service.add_xp_to_user") as mock_xp:
            result = check_and_award_badges("u1", "session_complete")

        mock_award.assert_not_called()
        mock_xp.assert_not_called()
        assert result["rank_update"] is None
        assert result["total_xp_earned"] == 0

    def test_award_badge_returning_none_excludes_it_from_results(self):
        """A badge that award_badge() can't confirm (e.g. lost a race to
        a concurrent request) shouldn't appear in new_badges or contribute XP."""
        p1, p2, p3, p4 = patch_state(streak={"current_streak": 0, "longest_streak": 0, "total_sessions": 0})
        with p1, p2, p3, p4, \
             patch("services.badge_service.award_badge", return_value=None), \
             patch("services.badge_service.add_xp_to_user") as mock_xp:
            result = check_and_award_badges("u1", "session_complete")

        assert result["new_badges"] == []
        assert result["total_xp_earned"] == 0
        mock_xp.assert_not_called()

    def test_exception_anywhere_in_flow_returns_safe_default(self):
        with patch(
            "services.badge_service.get_user_earned_badges",
            side_effect=RuntimeError("unexpected failure"),
        ):
            result = check_and_award_badges("u1", "session_complete")

        assert result == {"new_badges": [], "total_xp_earned": 0, "rank_update": None}


# =============================================================================
# check_badges_on_session_complete
# =============================================================================

class TestCheckBadgesOnSessionComplete:
    def test_always_fires_session_complete(self):
        with patch("services.badge_service.check_and_award_badges") as mock_check:
            mock_check.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}
            check_badges_on_session_complete("u1")

        mock_check.assert_any_call("u1", "session_complete")
        assert mock_check.call_count == 1  # no other flags set

    def test_perfect_score_fires_only_at_exactly_50(self):
        with patch("services.badge_service.check_and_award_badges") as mock_check:
            mock_check.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}
            check_badges_on_session_complete("u1", total_score=50)

        mock_check.assert_any_call("u1", "perfect_score")

    def test_score_below_50_does_not_fire_perfect_score(self):
        with patch("services.badge_service.check_and_award_badges") as mock_check:
            mock_check.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}
            check_badges_on_session_complete("u1", total_score=49)

        calls = [c.args for c in mock_check.call_args_list]
        assert ("u1", "perfect_score") not in calls

    def test_hard_difficulty_fires_hard_mode(self):
        with patch("services.badge_service.check_and_award_badges") as mock_check:
            mock_check.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}
            check_badges_on_session_complete("u1", difficulty="hard")

        mock_check.assert_any_call("u1", "hard_mode")

    def test_easy_difficulty_does_not_fire_hard_mode(self):
        with patch("services.badge_service.check_and_award_badges") as mock_check:
            mock_check.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}
            check_badges_on_session_complete("u1", difficulty="easy")

        calls = [c.args for c in mock_check.call_args_list]
        assert ("u1", "hard_mode") not in calls

    def test_simulation_flag_fires_simulation_event(self):
        with patch("services.badge_service.check_and_award_badges") as mock_check:
            mock_check.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}
            check_badges_on_session_complete("u1", is_simulation=True)

        mock_check.assert_any_call("u1", "simulation")

    def test_voice_flag_fires_voice_used_event(self):
        with patch("services.badge_service.check_and_award_badges") as mock_check:
            mock_check.return_value = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}
            check_badges_on_session_complete("u1", is_voice=True)

        mock_check.assert_any_call("u1", "voice_used")

    def test_all_flags_fire_all_five_events_and_merge_results(self):
        def fake_check(user_id, event, event_data=None):
            return {
                "new_badges": [{"id": event}],
                "total_xp_earned": 10,
                "rank_update": {"xp": event, "level": 1},
            }

        with patch("services.badge_service.check_and_award_badges", side_effect=fake_check):
            result = check_badges_on_session_complete(
                "u1", total_score=50, difficulty="hard", is_simulation=True, is_voice=True
            )

        badge_ids = [b["id"] for b in result["new_badges"]]
        assert badge_ids == [
            "session_complete", "perfect_score", "hard_mode", "simulation", "voice_used"
        ]
        assert result["total_xp_earned"] == 50  # 10 x 5 events
        # rank_update should reflect the LAST event processed (voice_used)
        assert result["rank_update"] == {"xp": "voice_used", "level": 1}


# =============================================================================
# _merge
# =============================================================================

class TestMerge:
    def test_extends_new_badges_and_sums_xp(self):
        base = {"new_badges": [{"id": "a"}], "total_xp_earned": 10, "rank_update": None}
        update = {"new_badges": [{"id": "b"}], "total_xp_earned": 5, "rank_update": None}

        _merge(base, update)

        assert base["new_badges"] == [{"id": "a"}, {"id": "b"}]
        assert base["total_xp_earned"] == 15

    def test_rank_update_overwritten_when_update_has_one(self):
        base = {"new_badges": [], "total_xp_earned": 0, "rank_update": {"xp": 1}}
        update = {"new_badges": [], "total_xp_earned": 0, "rank_update": {"xp": 2}}

        _merge(base, update)

        assert base["rank_update"] == {"xp": 2}

    def test_rank_update_preserved_when_update_has_none(self):
        base = {"new_badges": [], "total_xp_earned": 0, "rank_update": {"xp": 1}}
        update = {"new_badges": [], "total_xp_earned": 0, "rank_update": None}

        _merge(base, update)

        assert base["rank_update"] == {"xp": 1}