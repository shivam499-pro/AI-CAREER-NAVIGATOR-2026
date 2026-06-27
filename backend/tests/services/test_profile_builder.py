import pytest
from unittest.mock import patch

from services.profile_builder import (
    build_user_profile,
    get_user_documents,
    get_documents_by_type,
    DOCUMENT_WEIGHTS
)

# ----------------------------
# helper mock builder
# ----------------------------
class MockQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def execute(self):
        return type("Resp", (), {"data": self._data})


# ----------------------------
# build_user_profile tests
# ----------------------------

@patch("services.profile_builder.supabase")
def test_empty_user_profile(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = type(
        "Resp", (), {"data": []}
    )

    result = build_user_profile("user1")

    assert result == {"skills": []}


@patch("services.profile_builder.supabase")
def test_single_skill_single_doc(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = type(
        "Resp",
        (),
        {
            "data": [
                {
                    "document_type": "resume",
                    "extracted_data": {"skills": ["Python"]}
                }
            ]
        }
    )

    result = build_user_profile("user1")

    assert len(result["skills"]) == 1
    skill = result["skills"][0]

    assert skill["name"] == "Python"
    assert skill["count"] == 1
    assert "resume" in skill["sources"]
    assert "confidence" in skill


@patch("services.profile_builder.supabase")
def test_skill_aggregation(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = type(
        "Resp",
        (),
        {
            "data": [
                {"document_type": "resume", "extracted_data": {"skills": ["Python"]}},
                {"document_type": "certificate", "extracted_data": {"skills": ["python"]}},
            ]
        }
    )

    result = build_user_profile("user1")

    skill = result["skills"][0]

    assert skill["count"] == 2
    assert len(skill["sources"]) == 2
    assert "resume" in skill["sources"]
    assert "certificate" in skill["sources"]


@patch("services.profile_builder.supabase")
def test_unknown_document_type_weight(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = type(
        "Resp",
        (),
        {
            "data": [
                {"document_type": "unknown", "extracted_data": {"skills": ["Go"]}}
            ]
        }
    )

    result = build_user_profile("user1")

    skill = result["skills"][0]

    assert skill["confidence"] > 0


@patch("services.profile_builder.supabase")
def test_exception_returns_empty(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception(
        "DB error"
    )

    result = build_user_profile("user1")

    assert result == {"skills": []}


# ----------------------------
# get_user_documents
# ----------------------------

@patch("services.profile_builder.supabase")
def test_get_user_documents(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = type(
        "Resp", (), {"data": [{"id": 1}]}
    )

    result = get_user_documents("user1")

    assert isinstance(result, list)
    assert result[0]["id"] == 1


# ----------------------------
# get_documents_by_type
# ----------------------------

@patch("services.profile_builder.supabase")
def test_get_documents_by_type(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = type(
        "Resp", (), {"data": [{"id": 1, "document_type": "resume"}]}
    )

    result = get_documents_by_type("user1", "resume")

    assert result[0]["document_type"] == "resume"