"""
Tests for repositories/analysis_repository.py

The abstract AnalysisRepository is exercised indirectly everywhere else via
mock repositories, but the concrete SupabaseAnalysisRepository (the class
that actually talks to Supabase) was never directly tested. This file closes
that gap: success paths and exception paths for both get_by_user_id and
upsert, plus a smoke test on the ABC contract itself.
"""
import pytest
from unittest.mock import patch, MagicMock

from repositories.analysis_repository import (
    AnalysisRepository,
    SupabaseAnalysisRepository,
)


# ─── Abstract base class contract ─────────────────────────────────────────

def test_analysis_repository_is_abstract_and_cannot_be_instantiated():
    with pytest.raises(TypeError):
        AnalysisRepository()


def test_supabase_analysis_repository_is_a_valid_subclass():
    repo = SupabaseAnalysisRepository()
    assert isinstance(repo, AnalysisRepository)


# ─── get_by_user_id ────────────────────────────────────────────────────────

def _make_repo_with_mock_supabase(mock_supabase):
    """Build a SupabaseAnalysisRepository whose _get_supabase is patched."""
    repo = SupabaseAnalysisRepository()
    repo._get_supabase = lambda: mock_supabase
    return repo


def test_get_by_user_id_returns_first_row_when_data_present():
    mock_supabase = MagicMock()
    mock_response = MagicMock(data=[{"user_id": "u1", "strengths": ["Python"]}])
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

    repo = _make_repo_with_mock_supabase(mock_supabase)
    result = repo.get_by_user_id("u1")

    assert result == {"user_id": "u1", "strengths": ["Python"]}
    mock_supabase.table.assert_called_once_with("analyses")
    mock_supabase.table.return_value.select.assert_called_once_with("*")
    mock_supabase.table.return_value.select.return_value.eq.assert_called_once_with("user_id", "u1")


def test_get_by_user_id_returns_none_when_no_rows():
    mock_supabase = MagicMock()
    mock_response = MagicMock(data=[])
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

    repo = _make_repo_with_mock_supabase(mock_supabase)
    result = repo.get_by_user_id("missing-user")

    assert result is None


def test_get_by_user_id_returns_none_and_swallows_exception_on_failure():
    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = Exception("connection refused")

    repo = _make_repo_with_mock_supabase(mock_supabase)
    result = repo.get_by_user_id("u1")

    assert result is None


# ─── upsert ─────────────────────────────────────────────────────────────────

def test_upsert_returns_true_when_supabase_returns_data():
    mock_supabase = MagicMock()
    mock_response = MagicMock(data=[{"user_id": "u1"}])
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = mock_response

    repo = _make_repo_with_mock_supabase(mock_supabase)
    result = repo.upsert({"user_id": "u1", "strengths": ["Python"]})

    assert result is True
    mock_supabase.table.assert_called_once_with("analyses")
    mock_supabase.table.return_value.upsert.assert_called_once_with(
        {"user_id": "u1", "strengths": ["Python"]}, on_conflict="user_id"
    )


def test_upsert_returns_false_when_supabase_returns_empty_data():
    mock_supabase = MagicMock()
    mock_response = MagicMock(data=[])
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = mock_response

    repo = _make_repo_with_mock_supabase(mock_supabase)
    result = repo.upsert({"user_id": "u1"})

    assert result is False


def test_upsert_returns_false_and_swallows_exception_on_failure():
    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = Exception("timeout")

    repo = _make_repo_with_mock_supabase(mock_supabase)
    result = repo.upsert({"user_id": "u1"})

    assert result is False


def test_repository_init_wires_up_get_supabase_lazily():
    """__init__ should store the get_supabase callable, not call it eagerly."""
    with patch("core.supabase_client.get_supabase") as mock_get_supabase:
        repo = SupabaseAnalysisRepository()
        mock_get_supabase.assert_not_called()
        assert repo._get_supabase is mock_get_supabase