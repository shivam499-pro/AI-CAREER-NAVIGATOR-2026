from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.profile_enhanced import router

# ---------------------------------------------------
# Test App
# ---------------------------------------------------

app = FastAPI()
app.include_router(router)

client = TestClient(app)


# ---------------------------------------------------
# Dependency Override
# ---------------------------------------------------

def override_get_current_user():
    return SimpleNamespace(id="user-123")


app.dependency_overrides = {}


@pytest.fixture(autouse=True)
def setup_auth_override():
    from lib.auth import get_current_user

    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    yield

    app.dependency_overrides.clear()


# ---------------------------------------------------
# GET /enhanced
# ---------------------------------------------------

def test_get_enhanced_profile_success(mocker):
    mock_execute = MagicMock()

    mock_execute.data = [{
        "college_name": "Saveetha",
        "degree": "BTech",
        "branch": "CSE",
        "cgpa": "8.9",
        "extra_skills": ["Python"],
        "experience": [],
        "certificates": [],
        "target_companies": ["Google"],
    }]

    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .execute.return_value
    ) = mock_execute

    response = client.get("/enhanced")

    assert response.status_code == 200

    data = response.json()

    assert data["college_name"] == "Saveetha"
    assert data["degree"] == "BTech"


def test_get_enhanced_profile_not_found(mocker):
    mock_execute = MagicMock()
    mock_execute.data = []

    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .execute.return_value
    ) = mock_execute

    response = client.get("/enhanced")

    assert response.status_code == 200

    assert response.json()["error"] == (
        "Profile not found"
    )


def test_get_enhanced_profile_failure(mocker):
    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .execute.side_effect
    ) = Exception("DB failure")

    response = client.get("/enhanced")

    assert response.status_code == 200

    assert "DB failure" in response.json()["error"]


# ---------------------------------------------------
# POST /enhanced
# ---------------------------------------------------

def test_save_enhanced_profile_success(mocker):
    mock_execute = MagicMock()
    mock_execute.data = [{"id": 1}]

    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    (
        mock_supabase.table.return_value
        .upsert.return_value
        .execute.return_value
    ) = mock_execute

    payload = {
        "user_id": "user-123",
        "user_type": "student",
        "college_name": "Saveetha",
        "degree": "BTech"
    }

    response = client.post(
        "/enhanced",
        json=payload
    )

    assert response.status_code == 200

    assert response.json()["success"] is True


def test_save_enhanced_profile_failure(mocker):
    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    (
        mock_supabase.table.return_value
        .upsert.return_value
        .execute.side_effect
    ) = Exception("Insert failed")

    payload = {
        "user_id": "user-123",
        "user_type": "student"
    }

    response = client.post(
        "/enhanced",
        json=payload
    )

    assert response.status_code == 500

    assert "Insert failed" in response.json()["detail"]


def test_save_enhanced_profile_validation_error():
    response = client.post(
        "/enhanced",
        json={}
    )

    assert response.status_code == 422


# ---------------------------------------------------
# GET /progress
# ---------------------------------------------------

def test_get_user_progress_complete(mocker):
    profile_res = MagicMock()
    profile_res.data = [{
        "github_username": "jai",
        "leetcode_username": "jai"
    }]

    analysis_res = MagicMock()
    analysis_res.data = [{"id": 1}]

    interview_res = MagicMock()
    interview_res.data = [{"id": 1}]

    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    table_mock = (
        mock_supabase.table.return_value
    )

    table_mock.select.return_value.eq.return_value.execute.side_effect = [
        profile_res,
        analysis_res,
        interview_res
    ]

    response = client.get("/progress")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 100
    assert data["status"] == "ELITE"


def test_get_user_progress_partial(mocker):
    from unittest.mock import MagicMock
    from routers.profile_enhanced import get_current_user

    profile_res = MagicMock()
    profile_res.data = [{"user_id": "test-user"}]

    analysis_res = MagicMock()
    analysis_res.data = []

    interview_res = MagicMock()
    interview_res.data = []

    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    def table_side_effect(table_name):
        table_mock = MagicMock()

        query_mock = MagicMock()

        if table_name == "profiles":
            query_mock.execute.return_value = profile_res

        elif table_name == "analyses":
            query_mock.execute.return_value = analysis_res

        elif table_name == "interviews":
            query_mock.execute.return_value = interview_res

        table_mock.select.return_value = query_mock

        query_mock.eq.return_value = query_mock

        return table_mock

    mock_supabase.table.side_effect = table_side_effect

    # Mock authenticated user
    mock_user = MagicMock()
    mock_user.id = "test-user"

    app.dependency_overrides[get_current_user] = (
        lambda: mock_user
    )

    response = client.get("/progress")

    data = response.json()

    print(data)

    assert response.status_code == 200
    assert data["total"] == 25
    assert data["status"] == "INITIALIZED"

    # Cleanup
    app.dependency_overrides = {}



def test_get_user_progress_failure(mocker):
    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .execute.side_effect
    ) = Exception("Progress failure")

    response = client.get("/progress")

    data = response.json()

    assert data["total"] == 0
    assert "error" in data


# ---------------------------------------------------
# GET /match-fit
# ---------------------------------------------------

def test_get_match_fit_success(mocker):
    profile_res = MagicMock()
    profile_res.data = [{
        "career_goal": "Backend Engineer"
    }]

    analysis_res = MagicMock()
    analysis_res.data = [{
        "career_paths": [
            {
                "name": "Backend Engineer",
                "match_percentage": 92,
                "reason": "Excellent alignment"
            }
        ]
    }]

    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    table_mock = (
        mock_supabase.table.return_value
    )

    table_mock.select.return_value.eq.return_value.execute.side_effect = [
        profile_res,
        analysis_res
    ]

    response = client.get("/match-fit")

    assert response.status_code == 200

    data = response.json()

    assert data["score"] == 92
    assert data["label"] == "ELITE ALIGNMENT"


def test_get_match_fit_no_analysis(mocker):
    profile_res = MagicMock()
    profile_res.data = [{
        "career_goal": "AI Engineer"
    }]

    analysis_res = MagicMock()
    analysis_res.data = []

    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    table_mock = (
        mock_supabase.table.return_value
    )

    table_mock.select.return_value.eq.return_value.execute.side_effect = [
        profile_res,
        analysis_res
    ]

    response = client.get("/match-fit")

    data = response.json()

    assert data["score"] == 0

    assert data["label"] == (
        "Optimization Required"
    )


def test_get_match_fit_no_match_path(mocker):
    profile_res = MagicMock()
    profile_res.data = [{
        "career_goal": "DevOps"
    }]

    analysis_res = MagicMock()
    analysis_res.data = [{
        "career_paths": []
    }]

    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    table_mock = (
        mock_supabase.table.return_value
    )

    table_mock.select.return_value.eq.return_value.execute.side_effect = [
        profile_res,
        analysis_res
    ]

    response = client.get("/match-fit")

    data = response.json()

    assert data["score"] == 0
    assert data["label"] == "No Data"


def test_get_match_fit_failure(mocker):
    mock_supabase = mocker.patch(
        "routers.profile_enhanced.supabase"
    )

    (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .execute.side_effect
    ) = Exception("Match failure")

    response = client.get("/match-fit")

    data = response.json()

    assert data["score"] == 0
    assert "error" in data

def test_save_enhanced_profile_no_data_returned_raises_500(mocker):
    """upsert() succeeds without error but returns no data -- treated as a
    failure, not silently reported as success."""
    mock_supabase = mocker.patch("routers.profile_enhanced.supabase")
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=None)

    payload = {"user_id": "user-123", "user_type": "student"}
    response = client.post("/enhanced", json=payload)

    assert response.status_code == 500
    assert "Failed to save profile" in response.json()["detail"]

def test_get_match_fit_defaults_to_first_path_when_no_name_match(mocker):
    """target_goal is set but doesn't match any career_path name -- falls
    back to the first career path rather than returning 'No Data'."""
    profile_res = MagicMock()
    profile_res.data = [{"career_goal": "Backend Engineer"}]

    analysis_res = MagicMock()
    analysis_res.data = [{
        "career_paths": [
            {"name": "Frontend Engineer", "match_percentage": 60, "reason": "Some overlap"}
        ]
    }]

    mock_supabase = mocker.patch("routers.profile_enhanced.supabase")
    table_mock = mock_supabase.table.return_value
    table_mock.select.return_value.eq.return_value.execute.side_effect = [
        profile_res,
        analysis_res
    ]

    response = client.get("/match-fit")

    data = response.json()
    assert data["score"] == 60
    assert data["role"] == "Frontend Engineer"