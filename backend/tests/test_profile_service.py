import pytest
from unittest.mock import MagicMock
from services import profile_service


# -----------------------
# helpers
# -----------------------
def build_query_mock(response_data):
    query = MagicMock()

    query.execute.return_value = MagicMock(
        data=response_data
    )

    query.eq.return_value = query

    return query


def mock_supabase(mocker, return_data=None, side_effect=None):
    mock_client = MagicMock()

    execute_mock = MagicMock()

    if side_effect:
        execute_mock.execute.side_effect = side_effect
    else:
        execute_mock.execute.return_value = MagicMock(data=return_data)

    mock_client.table.return_value.select.return_value.eq.return_value.execute = execute_mock.execute
    mock_client.table.return_value.upsert.return_value.execute = execute_mock.execute
    mock_client.table.return_value.select.return_value.execute = execute_mock.execute

    mocker.patch("services.profile_service.get_supabase", return_value=mock_client)
    return mock_client


# -----------------------
# get_profile_by_user_id
# -----------------------

def test_get_profile_success(mocker):
    mock_supabase(mocker, return_data=[{"user_id": "u1", "name": "John"}])

    result = profile_service.get_profile_by_user_id("u1")

    assert result["user_id"] == "u1"


def test_get_profile_not_found(mocker):
    mock_supabase(mocker, return_data=None)

    result = profile_service.get_profile_by_user_id("u1")

    assert result is None


def test_get_profile_exception(mocker):
    mock_supabase(mocker, side_effect=Exception("DB crash"))

    result = profile_service.get_profile_by_user_id("u1")

    assert result is None


# -----------------------
# save_profile
# -----------------------

def test_save_profile_success(mocker):
    mock_supabase(mocker, return_data=[{"user_id": "u1"}])

    result = profile_service.save_profile("u1", {"name": "John"})

    assert result is True


def test_save_profile_failure(mocker):
    mock_supabase(mocker, side_effect=Exception("fail"))

    result = profile_service.save_profile("u1", {"name": "John"})

    assert result is False


# -----------------------
# merge_skills_from_documents
# -----------------------

def test_merge_skills_success(mocker):
    mock_client = MagicMock()

    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[
            {
                "document_type": "resume",
                "extracted_data": {
                    "skills": ["Python", "FastAPI"]
                }
            },
            {
                "document_type": "certificate",
                "extracted_data": {
                    "skills": ["python", "Docker"]
                }
            }
        ]
    )

    mocker.patch("services.profile_service.get_supabase", return_value=mock_client)

    result = profile_service.merge_skills_from_documents("u1")

    assert len(result) > 0
    assert any(s["name"].lower() == "python" for s in result)


def test_merge_skills_empty(mocker):
    mock_supabase(mocker, return_data=None)

    result = profile_service.merge_skills_from_documents("u1")

    assert result == []


# -----------------------
# calculate_profile_completeness
# -----------------------

def test_profile_completeness_full_profile():
    profile = {
        "college_name": "ABC",
        "degree": "BE",
        "branch": "CSE",
        "github_username": "git",
        "leetcode_username": "leet",
        "extra_skills": ["a", "b", "c"],
        "resume_text": "something"
    }

    docs = [{"document_type": "resume"}]

    score = profile_service.calculate_profile_completeness(profile, docs)

    assert score == 100


def test_profile_completeness_empty():
    assert profile_service.calculate_profile_completeness(None, []) == 0


# -----------------------
# get_enriched_profile
# -----------------------

def test_enriched_profile_not_found(mocker):
    mock_supabase(mocker, return_data=None)

    result = profile_service.get_enriched_profile("u1")

    assert result["exists"] is False

def test_enriched_profile_success(mocker):
    mock_client = MagicMock()

    # --- profile table ---
    profile_exec = MagicMock()
    profile_exec.execute.return_value = MagicMock(
        data=[{
            "user_id": "u1",
            "extra_skills": ["Python"]
        }]
    )

    # --- documents table ---
    docs_exec = MagicMock()
    docs_exec.execute.return_value = MagicMock(
        data=[]
    )

    def table_side_effect(name):
        table = MagicMock()

        if name == "profiles":
            table.select.return_value = build_query_mock([
                {"user_id": "u1"}
            ])
        elif name == "analyses":
            table.select.return_value = build_query_mock([
                {"id": 1}
            ])
        elif name == "interviews":
            table.select.return_value = build_query_mock([
                {"id": 1}
            ])
        return table

    mock_client.table.side_effect = table_side_effect

    mocker.patch("services.profile_service.get_supabase", return_value=mock_client)

    result = profile_service.get_enriched_profile("u1")

    assert result["exists"] is True
    assert "skills" in result

# -----------------------
# get_user_progress
# -----------------------

def test_user_progress_happy_path(mocker):
    mock_client = MagicMock()

    # --- profile table ---
    profile_exec = MagicMock()
    profile_exec.execute.return_value = MagicMock(
        data=[{"user_id": "u1", "github_username": "x"}]
    )

    # --- analyses table ---
    analyses_exec = MagicMock()
    analyses_exec.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )

    # --- interviews table ---
    interviews_exec = MagicMock()
    interviews_exec.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )

    def table_side_effect(name):
        if name == "profiles":
            return MagicMock(
                select=lambda *args, **kwargs: MagicMock(
                    eq=lambda *a, **k: MagicMock(execute=profile_exec.execute)
                )
            )
        if name == "analyses":
            return MagicMock(
                select=lambda *args, **kwargs: MagicMock(
                    eq=lambda *a, **k: MagicMock(execute=analyses_exec.execute)
                )
            )
        if name == "interviews":
            return MagicMock(
                select=lambda *args, **kwargs: MagicMock(
                    eq=lambda *a, **k: MagicMock(execute=interviews_exec.execute)
                )
            )

    mock_client.table.side_effect = table_side_effect

    mocker.patch("services.profile_service.get_supabase", return_value=mock_client)

    result = profile_service.get_user_progress("u1")

    assert "steps" in result
    assert result["total"] > 0


def test_user_progress_exception(mocker):
    mock_supabase(mocker, side_effect=Exception("fail"))

    result = profile_service.get_user_progress("u1")

    assert "error" in result



def test_merge_skills_no_documents(monkeypatch):
    from services.profile_service import merge_skills_from_documents

    class FakeSupabase:
        def table(self, name):
            return self

        def select(self, *args):
            return self

        def eq(self, *args):
            return self

        def execute(self):
            return type("R", (), {"data": []})()

    monkeypatch.setattr("services.profile_service.get_supabase", lambda: FakeSupabase())

    result = merge_skills_from_documents("user-1")

    assert result == []


def test_merge_skills_confidence_and_sort(monkeypatch):
    from services.profile_service import merge_skills_from_documents

    fake_data = [
        {
            "document_type": "resume",
            "extracted_data": {
                "skills": ["Python", "FastAPI"]
            }
        },
        {
            "document_type": "certificate",
            "extracted_data": {
                "skills": ["python", "Docker"]
            }
        }
    ]

    class FakeSupabase:
        def table(self, name):
            return self

        def select(self, *args):
            return self

        def eq(self, *args):
            return self

        def execute(self):
            return type("R", (), {"data": fake_data})()

    monkeypatch.setattr("services.profile_service.get_supabase", lambda: FakeSupabase())

    result = merge_skills_from_documents("user-1")

    skill_names = [s["name"].lower() for s in result]

    assert "python" in skill_names
    assert "fastapi" in skill_names
    assert "docker" in skill_names

    # confidence computed
    for s in result:
        assert "confidence" in s
        assert 0 <= s["confidence"] <= 1


# -----------------------
# merge_skills_from_documents: blank-skill guard (line 92-93)
# -----------------------

def test_merge_skills_skips_blank_skill_names(mocker):
    """A skill that is empty or whitespace-only after strip() must be
    dropped, not counted as a real skill."""
    mock_supabase(mocker, return_data=[
        {
            "document_type": "resume",
            "extracted_data": {"skills": ["Python", "   ", ""]}
        }
    ])

    result = profile_service.merge_skills_from_documents("u1")

    skill_names = [s["name"].lower() for s in result]

    assert skill_names == ["python"]


# -----------------------
# merge_skills_from_documents: exception path (line 121-123)
# -----------------------

def test_merge_skills_from_documents_exception(mocker):
    """If the documents query blows up, the function must swallow the
    error and return an empty list rather than propagate."""
    mock_supabase(mocker, side_effect=Exception("DB down"))

    result = profile_service.merge_skills_from_documents("u1")

    assert result == []


# -----------------------
# calculate_profile_completeness: resume_text fallback (line 169-170)
# -----------------------

def test_profile_completeness_resume_text_fallback():
    """When there's no uploaded resume DOCUMENT, a resume_text field on
    the profile itself should still grant the resume credit."""
    profile = {
        "college_name": "ABC",
        "resume_text": "Experienced engineer with 5 years..."
    }

    # No documents at all -> has_resume stays False -> must fall through
    # to the elif branch on profile.resume_text
    score = profile_service.calculate_profile_completeness(profile, documents=[])

    # college_name (10) + resume_text fallback (20) = 30
    assert score == 30


def test_profile_completeness_no_resume_anywhere():
    """Sanity check for the same branch: no document AND no resume_text
    means neither path awards the 20 points."""
    profile = {"college_name": "ABC"}

    score = profile_service.calculate_profile_completeness(profile, documents=[])

    assert score == 10


# -----------------------
# get_enriched_profile: documents-fetch exception path (line 202-204)
# -----------------------

def test_enriched_profile_documents_fetch_exception(mocker):
    """If fetching user_documents blows up, get_enriched_profile should
    degrade gracefully to an empty documents list instead of crashing."""
    mocker.patch(
        "services.profile_service.get_profile_by_user_id",
        return_value={"user_id": "u1"}
    )
    mocker.patch(
        "services.profile_service.get_supabase",
        side_effect=Exception("Supabase unreachable")
    )

    result = profile_service.get_enriched_profile("u1")

    assert result["exists"] is True
    assert result["documents_count"] == 0
    assert result["skills"] == []


# -----------------------
# get_enriched_profile: document-skill and manual-skill merge loops
# (line 216-217 and 224-225)
# -----------------------

def test_enriched_profile_merges_document_and_manual_skills(mocker):
    """Document-sourced skills should be tagged 'document'; manual
    skills not already present should be tagged 'manual'; a manual
    skill that duplicates a document skill must NOT be added twice."""
    mocker.patch(
        "services.profile_service.get_profile_by_user_id",
        return_value={"user_id": "u1", "extra_skills": ["Python", "SQL"]}
    )
    mock_supabase(mocker, return_data=[
        {
            "document_type": "resume",
            "extracted_data": {"skills": ["Python", "Docker"]}
        }
    ])

    result = profile_service.get_enriched_profile("u1")

    by_name = {s["name"].lower(): s for s in result["skills"]}

    # document-sourced skills came through the doc_skill loop
    assert by_name["python"]["source"] == "document"
    assert by_name["docker"]["source"] == "document"

    # "SQL" is genuinely new -> added via the manual-skill loop
    assert by_name["sql"]["source"] == "manual"
    assert by_name["sql"]["confidence"] == 0.8

    # "Python" already existed as a document skill -> not duplicated
    assert sum(1 for s in result["skills"] if s["name"].lower() == "python") == 1
    assert result["documents_count"] == 1