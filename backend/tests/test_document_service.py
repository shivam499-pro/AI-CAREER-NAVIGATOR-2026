"""
Tests for services.document_service
"""

import pytest
from unittest.mock import MagicMock, patch

from services.document_service import (
    TECH_SKILLS,
    extract_basic_skills,
    save_document,
    get_user_documents,
    get_documents_by_type,
    get_document_by_id,
    delete_document,
    extract_skills_from_resume,
)


# =========================================================
# extract_basic_skills
# =========================================================

def test_extract_basic_skills_happy_path():
    text = """
    Python developer with FastAPI, Docker,
    PostgreSQL, React and AWS experience.
    """

    result = extract_basic_skills(text)

    assert "python" in result
    assert "fastapi" in result
    assert "docker" in result
    assert "postgresql" in result
    assert "react" in result
    assert "aws" in result


def test_extract_basic_skills_case_insensitive():
    text = "PYTHON python Python React REACT"

    result = extract_basic_skills(text)

    assert "python" in result
    assert "react" in result


def test_extract_basic_skills_deduplication():
    text = """
    Python python PYTHON
    Docker docker DOCKER
    """

    result = extract_basic_skills(text)

    assert result.count("python") == 1
    assert result.count("docker") == 1


def test_extract_basic_skills_empty_input():
    assert extract_basic_skills("") == []
    assert extract_basic_skills(None) == []


def test_extract_basic_skills_garbage_text():
    text = """
    lorem ipsum banana elephant random words
    """

    result = extract_basic_skills(text)

    # should not falsely match
    assert result == []


def test_extract_basic_skills_multiple_categories():
    text = """
    Python JavaScript React Docker Kubernetes
    TensorFlow PostgreSQL Git Linux
    """

    result = extract_basic_skills(text)

    expected = {
        "python",
        "javascript",
        "react",
        "docker",
        "kubernetes",
        "tensorflow",
        "postgresql",
        "git",
        "linux",
    }

    assert expected.issubset(set(result))


# =========================================================
# save_document
# =========================================================

@patch("services.document_service.get_supabase")
def test_save_document_success(mock_get_supabase):
    mock_response = MagicMock()
    mock_response.data = [{"id": 101}]

    mock_supabase = MagicMock()
    (
        mock_supabase.table.return_value
        .insert.return_value
        .execute.return_value
    ) = mock_response

    mock_get_supabase.return_value = mock_supabase

    result = save_document(
        user_id="user-1",
        document_name="resume.pdf",
        document_type="resume",
        storage_url="https://storage.test/resume.pdf",
        extracted_data={"skills": ["python"]}
    )

    assert result == 101


@patch("services.document_service.get_supabase")
def test_save_document_without_optional_fields(mock_get_supabase):
    mock_response = MagicMock()
    mock_response.data = [{"id": 55}]

    mock_supabase = MagicMock()

    (
        mock_supabase.table.return_value
        .insert.return_value
        .execute.return_value
    ) = mock_response

    mock_get_supabase.return_value = mock_supabase

    result = save_document(
        user_id="user-1",
        document_name="doc.txt",
        document_type="other"
    )

    assert result == 55


@patch("services.document_service.get_supabase")
def test_save_document_empty_response(mock_get_supabase):
    mock_response = MagicMock()
    mock_response.data = []

    mock_supabase = MagicMock()

    (
        mock_supabase.table.return_value
        .insert.return_value
        .execute.return_value
    ) = mock_response

    mock_get_supabase.return_value = mock_supabase

    result = save_document(
        user_id="user-1",
        document_name="resume.pdf",
        document_type="resume"
    )

    assert result is None


@patch("services.document_service.get_supabase")
def test_save_document_supabase_failure(mock_get_supabase):
    mock_get_supabase.side_effect = Exception("Supabase failure")

    result = save_document(
        user_id="user-1",
        document_name="resume.pdf",
        document_type="resume"
    )

    assert result is None


# =========================================================
# get_user_documents
# =========================================================

@patch("services.document_service.get_supabase")
def test_get_user_documents_success(mock_get_supabase):
    docs = [
        {
            "id": 1,
            "document_name": "resume.pdf",
            "document_type": "resume"
        }
    ]

    mock_response = MagicMock()
    mock_response.data = docs

    mock_supabase = MagicMock()

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .order.return_value
        .execute.return_value
    ) = mock_response

    mock_get_supabase.return_value = mock_supabase

    result = get_user_documents("user-1")

    assert result == docs


@patch("services.document_service.get_supabase")
def test_get_user_documents_empty(mock_get_supabase):
    mock_response = MagicMock()
    mock_response.data = []

    mock_supabase = MagicMock()

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .order.return_value
        .execute.return_value
    ) = mock_response

    mock_get_supabase.return_value = mock_supabase

    result = get_user_documents("user-1")

    assert result == []


@patch("services.document_service.get_supabase")
def test_get_user_documents_failure(mock_get_supabase):
    mock_get_supabase.side_effect = Exception("DB failure")

    result = get_user_documents("user-1")

    assert result == []


# =========================================================
# get_documents_by_type
# =========================================================

@patch("services.document_service.get_supabase")
def test_get_documents_by_type_success(mock_get_supabase):
    docs = [
        {
            "id": 1,
            "document_type": "resume"
        }
    ]

    mock_response = MagicMock()
    mock_response.data = docs

    mock_supabase = MagicMock()

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .execute.return_value
    ) = mock_response

    mock_get_supabase.return_value = mock_supabase

    result = get_documents_by_type(
        "user-1",
        "resume"
    )

    assert result == docs


@patch("services.document_service.get_supabase")
def test_get_documents_by_type_failure(mock_get_supabase):
    mock_get_supabase.side_effect = Exception("DB failure")

    result = get_documents_by_type(
        "user-1",
        "resume"
    )

    assert result == []


# =========================================================
# get_document_by_id
# =========================================================

@patch("services.document_service.get_supabase")
def test_get_document_by_id_success(mock_get_supabase):
    doc = {
        "id": 1,
        "document_name": "resume.pdf"
    }

    mock_response = MagicMock()
    mock_response.data = [doc]

    mock_supabase = MagicMock()

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .execute.return_value
    ) = mock_response

    mock_get_supabase.return_value = mock_supabase

    result = get_document_by_id(1)

    assert result == doc


@patch("services.document_service.get_supabase")
def test_get_document_by_id_not_found(mock_get_supabase):
    mock_response = MagicMock()
    mock_response.data = []

    mock_supabase = MagicMock()

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .execute.return_value
    ) = mock_response

    mock_get_supabase.return_value = mock_supabase

    result = get_document_by_id(999)

    assert result is None


@patch("services.document_service.get_supabase")
def test_get_document_by_id_failure(mock_get_supabase):
    mock_get_supabase.side_effect = Exception("DB failure")

    result = get_document_by_id(1)

    assert result is None


# =========================================================
# delete_document
# =========================================================

@patch("services.document_service.get_supabase")
def test_delete_document_success(mock_get_supabase):
    mock_response = MagicMock()

    mock_supabase = MagicMock()

    (
        mock_supabase.table.return_value
        .delete.return_value
        .eq.return_value
        .eq.return_value
        .execute.return_value
    ) = mock_response

    mock_get_supabase.return_value = mock_supabase

    result = delete_document(1, "user-1")

    assert result is True


@patch("services.document_service.get_supabase")
def test_delete_document_failure(mock_get_supabase):
    mock_get_supabase.side_effect = Exception("DB failure")

    result = delete_document(1, "user-1")

    assert result is False


# =========================================================
# extract_skills_from_resume
# =========================================================

def test_extract_skills_from_resume_happy_path():
    text = """
    Python FastAPI Docker PostgreSQL AWS
    """

    result = extract_skills_from_resume(text)

    assert "skills" in result
    assert "experience" in result
    assert "education" in result

    assert "python" in result["skills"]
    assert "docker" in result["skills"]


def test_extract_skills_from_resume_empty():
    result = extract_skills_from_resume("")

    assert result == {
        "skills": [],
        "experience": [],
        "education": []
    }


def test_extract_skills_from_resume_none():
    result = extract_skills_from_resume(None)

    assert result == {
        "skills": [],
        "experience": [],
        "education": []
    }


def test_extract_skills_from_resume_garbage():
    result = extract_skills_from_resume(
        "banana elephant lorem ipsum"
    )

    assert result["skills"] == []


# =========================================================
# TECH_SKILLS integrity
# =========================================================

def test_tech_skills_structure():
    assert isinstance(TECH_SKILLS, set)
    assert len(TECH_SKILLS) > 0

    assert "python" in TECH_SKILLS
    assert "react" in TECH_SKILLS
    assert "docker" in TECH_SKILLS
