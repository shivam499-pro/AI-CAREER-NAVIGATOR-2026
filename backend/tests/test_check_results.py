"""
Tests for check_results.py

Coverage targets (33 missing lines → 100%):
- check_real_analysis(): no data, minimal data, full data with
  career_paths, roadmap with milestones, and all print paths.

NOTE: check_results.py is a CLI/debug script that directly calls
supabase via create_client. We mock at the module boundary.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from io import StringIO


# ---------------------------------------------------------------------------
# Helper: build the analysis dict the way supabase would return it
# ---------------------------------------------------------------------------

def _make_analysis(
    experience_level="Mid",
    strengths=None,
    career_paths=None,
    roadmap=None,
) -> dict:
    return {
        "experience_level": experience_level,
        "strengths": strengths or ["Python", "FastAPI"],
        "career_paths": career_paths or [],
        "roadmap": roadmap or {},
    }


def _make_career_path(name="Backend Engineer", match=88, reason="Strong API skills"):
    return {"name": name, "match_percentage": match, "reason": reason}


def _make_roadmap(target="Staff Engineer", weeks=24, milestones=None):
    """
    NOTE: uses an explicit `is None` check, not `milestones or [...]`.
    An empty list `[]` is falsy in Python, so `milestones or [default]`
    would silently replace an intentionally-empty list with the default
    — exactly the bug that caused test_analysis_with_roadmap_but_no_milestones
    to fail. Tests that pass milestones=[] need that empty list preserved.
    """
    return {
        "target_career": target,
        "total_weeks": weeks,
        "milestones": [{"title": "Learn system design"}] if milestones is None else milestones,
    }


# ===========================================================================
# check_real_analysis()
# ===========================================================================


class TestCheckRealAnalysis:
    """
    Each test patches `create_client` so no real network calls are made.
    We capture stdout to verify print output.
    """

    def _patch_supabase(self, data):
        """Return a context manager that mocks supabase with given data."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=data
        )
        return patch("check_results.create_client", return_value=mock_client)

    def test_no_analysis_found_prints_message_and_returns(self, capsys):
        """When DB returns empty list → prints 'No analysis found' and exits early."""
        with self._patch_supabase([]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "No analysis found" in captured.out

    def test_no_analysis_does_not_print_summary_header(self, capsys):
        """Early return means the summary block never prints."""
        with self._patch_supabase([]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "REAL AI ANALYSIS SUMMARY" not in captured.out

    def test_analysis_prints_experience_level(self, capsys):
        """Valid analysis → experience level printed."""
        analysis = _make_analysis(experience_level="Senior")
        with self._patch_supabase([analysis]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "Senior" in captured.out

    def test_analysis_prints_strengths(self, capsys):
        """Strengths list joined and printed."""
        analysis = _make_analysis(strengths=["Go", "Kubernetes", "Postgres"])
        with self._patch_supabase([analysis]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "Go" in captured.out
        assert "Kubernetes" in captured.out
        assert "Postgres" in captured.out

    def test_analysis_with_career_paths_prints_top_path(self, capsys):
        """career_paths present → first path name, match %, and reason printed."""
        career_paths = [
            _make_career_path("ML Engineer", 92, "Strong in Python and data"),
            _make_career_path("Backend Engineer", 75, "Good API skills"),
        ]
        analysis = _make_analysis(career_paths=career_paths)
        with self._patch_supabase([analysis]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "ML Engineer" in captured.out
        assert "92" in captured.out
        assert "Strong in Python and data" in captured.out

    def test_analysis_with_no_career_paths_skips_career_section(self, capsys):
        """Empty career_paths list → career section skipped, no KeyError."""
        analysis = _make_analysis(career_paths=[])
        with self._patch_supabase([analysis]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        # Should not crash and summary header should still print
        assert "REAL AI ANALYSIS SUMMARY" in captured.out

    def test_analysis_with_roadmap_prints_title_and_weeks(self, capsys):
        """Roadmap present → target career and total weeks printed."""
        roadmap = _make_roadmap("Principal Engineer", 36)
        analysis = _make_analysis(roadmap=roadmap)
        with self._patch_supabase([analysis]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "Principal Engineer" in captured.out
        assert "36" in captured.out

    def test_analysis_with_roadmap_prints_first_milestone(self, capsys):
        """Roadmap with milestones → first milestone title printed."""
        milestones = [
            {"title": "Complete DSA bootcamp"},
            {"title": "Build 3 projects"},
        ]
        roadmap = _make_roadmap(milestones=milestones)
        analysis = _make_analysis(roadmap=roadmap)
        with self._patch_supabase([analysis]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "Complete DSA bootcamp" in captured.out
        assert "Build 3 projects" not in captured.out  # only first milestone

    def test_analysis_with_empty_roadmap_skips_roadmap_section(self, capsys):
        """Empty roadmap dict → roadmap section skipped, no error."""
        analysis = _make_analysis(roadmap={})
        with self._patch_supabase([analysis]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "Roadmap Title" not in captured.out

    def test_analysis_with_roadmap_but_no_milestones(self, capsys):
        """
        Roadmap present but milestones list is genuinely empty (now that
        the _make_roadmap helper bug is fixed) → milestones[0] is never
        indexed, so the 'Sample Week 1 Milestone:' print line never runs.
        """
        roadmap = _make_roadmap(milestones=[])
        analysis = _make_analysis(roadmap=roadmap)
        with self._patch_supabase([analysis]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "Sample Week 1 Milestone:" not in captured.out

    def test_fetching_user_id_is_printed(self, capsys):
        """The user_id being fetched is printed at the start."""
        with self._patch_supabase([]):
            from check_results import check_real_analysis
            check_real_analysis()

        captured = capsys.readouterr()
        assert "Fetching analysis for user" in captured.out

    def test_supabase_env_vars_are_read(self):
        """SUPABASE_URL and SUPABASE_SERVICE_KEY are used to create client."""
        with patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"},
        ):
            with patch("check_results.create_client") as mock_create:
                mock_client = MagicMock()
                mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
                mock_create.return_value = mock_client

                from check_results import check_real_analysis
                check_real_analysis()

                mock_create.assert_called_once_with("https://test.supabase.co", "test-key")

    def test_full_analysis_end_to_end(self, capsys):
        """Full analysis with all fields populated — all print branches hit."""
        career_paths = [_make_career_path("DevOps Engineer", 85, "Strong in Docker")]
        roadmap = _make_roadmap("Staff DevOps", 20, [{"title": "Get CKA cert"}])
        analysis = _make_analysis(
            experience_level="Mid-Senior",
            strengths=["Docker", "CI/CD", "Kubernetes"],
            career_paths=career_paths,
            roadmap=roadmap,
        )
        with self._patch_supabase([analysis]):
            from check_results import check_real_analysis
            check_real_analysis()

        out = capsys.readouterr().out
        assert "Mid-Senior" in out
        assert "Docker" in out
        assert "DevOps Engineer" in out
        assert "85" in out
        assert "Staff DevOps" in out
        assert "20" in out
        assert "Get CKA cert" in out