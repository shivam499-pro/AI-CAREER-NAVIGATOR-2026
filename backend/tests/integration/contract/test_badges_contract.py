"""
Badges Contract Tests
badgesClient.ts expects exact response shapes.
useBadges.ts derives earnedBadges, lockedBadges from these.
"""
import pytest
from unittest.mock import patch, MagicMock
from tests.integration.conftest import TEST_USER_ID, make_supabase_response

@pytest.mark.integration
class TestBadgesContract:

    def test_get_badges_response_shape(self, authed_client, mock_supabase):
        """
        badgesClient.getBadges() expects:
        { earned: Badge[], all_badges: AllBadge[], pagination: {...} }
        
        useBadges derives lockedBadges by filtering all_badges.
        Missing field → lockedBadges is always empty.
        """
        mock_badges = [
            {
                "badge_id": "first_session",
                "name": "First Session",
                "emoji": "🎯",
                "description": "Completed first interview",
                "earned_at": "2026-06-01T10:00:00Z"
            }
        ]
        mock_all_badges = [
            {"badge_id": "first_session", "name": "First Session", "emoji": "🎯", "description": "..."},
            {"badge_id": "perfect_score", "name": "Perfect Score", "emoji": "⭐", "description": "..."},
        ]
        
        mock_supabase.table.return_value.select.return_value\
            .eq.return_value.execute.return_value = \
            MagicMock(data=mock_badges, count=len(mock_badges))

        response = authed_client.get(f"/api/v1/badges/{TEST_USER_ID}?page=1&limit=50")

        assert response.status_code == 200
        body = response.json()
        
        assert "earned" in body, "earned array missing"
        assert "all_badges" in body, "all_badges missing — lockedBadges always empty"
        assert "pagination" in body, "pagination missing"
        
        if body["earned"]:
            badge = body["earned"][0]
            for field in ["badge_id", "name", "emoji", "description"]:
                assert field in badge, f"Badge field '{field}' missing"

    def test_badge_check_response_has_newly_earned(self, authed_client, mock_supabase):
        """
        After interview, frontend checks badges:
        if (sessionData.new_badges?.length > 0) → toast
        Response must include newly_earned array.
        """
        with patch("services.badge_service.check_and_award_badges") as mock_check:
            mock_check.return_value = {
                "newly_earned": [
                    {"badge_id": "first_session", "name": "First Session", "emoji": "🎯", "description": "..."}
                ]
            }
            
            response = authed_client.post(
                f"/api/v1/badges/check",
                json={"user_id": TEST_USER_ID, "event": "session_complete"}
            )
        
        assert response.status_code == 200
        body = response.json()
        assert "newly_earned" in body, "newly_earned missing — badge toasts never show"