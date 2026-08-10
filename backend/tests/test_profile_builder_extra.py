"""
Additional tests for services/profile_builder.py filling in coverage gaps
left by tests/services/test_profile_builder.py:

- build_user_profile: blank/whitespace-only skill strings are skipped
- get_user_documents: empty-data branch and exception branch
- get_documents_by_type: empty-data branch and exception branch

Note: the `else: confidence = 0.0` branch (profile_builder.py line 94) is not
covered here — with the current implementation, `sources` is always
populated immediately after a skill entry is created, so that branch is
unreachable dead code, not a gap in test coverage.
"""
from unittest.mock import patch

from services.profile_builder import (
    build_user_profile,
    get_user_documents,
    get_documents_by_type,
)


# ─── build_user_profile: blank skill strings ───────────────────────────────

@patch("services.profile_builder.supabase")
def test_build_user_profile_skips_blank_and_whitespace_only_skills(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = type(
        "Resp",
        (),
        {
            "data": [
                {
                    "document_type": "resume",
                    "extracted_data": {"skills": ["", "   ", "Python"]},
                }
            ]
        },
    )

    result = build_user_profile("user1")

    assert len(result["skills"]) == 1
    assert result["skills"][0]["name"] == "Python"


# ─── get_user_documents: empty data / exception ────────────────────────────

@patch("services.profile_builder.supabase")
def test_get_user_documents_returns_empty_list_when_no_data(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = type(
        "Resp", (), {"data": None}
    )

    result = get_user_documents("user1")

    assert result == []


@patch("services.profile_builder.supabase")
def test_get_user_documents_returns_empty_list_on_exception(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception(
        "connection lost"
    )

    result = get_user_documents("user1")

    assert result == []


# ─── get_documents_by_type: empty data / exception ─────────────────────────

@patch("services.profile_builder.supabase")
def test_get_documents_by_type_returns_empty_list_when_no_data(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = type(
        "Resp", (), {"data": []}
    )

    result = get_documents_by_type("user1", "resume")

    assert result == []


@patch("services.profile_builder.supabase")
def test_get_documents_by_type_returns_empty_list_on_exception(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception(
        "query failed"
    )

    result = get_documents_by_type("user1", "resume")

    assert result == []