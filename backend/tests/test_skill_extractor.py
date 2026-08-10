import pytest
from unittest.mock import MagicMock, patch

from services.skill_extractor import (
    SkillExtractor,
    SKILL_CATEGORIES,
    extract_resume_skills,
    ai_extract_skills,
    compare_resume_to_job,
)


# =========================================================
# Fixtures
# =========================================================

@pytest.fixture
def extractor():
    return SkillExtractor()


# =========================================================
# Initialization
# =========================================================

def test_skill_extractor_init_without_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    extractor = SkillExtractor()

    assert extractor._supabase is None


@patch("services.skill_extractor.create_client")
def test_skill_extractor_init_with_env(mock_create_client, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")

    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    extractor = SkillExtractor()

    assert extractor._supabase == mock_client
    mock_create_client.assert_called_once()


# =========================================================
# extract_from_resume
# =========================================================

@pytest.mark.asyncio
async def test_extract_from_resume_happy_path(extractor):
    resume = """
    Python developer with experience in FastAPI, Docker,
    PostgreSQL, React, AWS, Git and Kubernetes.
    """

    result = await extractor.extract_from_resume(resume)

    assert "skills" in result
    assert "programming_languages" in result["skills"]
    assert "web_technologies" in result["skills"]

    assert "python" in result["skills"]["programming_languages"]
    assert "fastapi" in result["skills"]["web_technologies"]
    assert "docker" in result["skills"]["cloud_infrastructure"]

    assert result["total_count"] > 0
    assert "extracted_at" in result


@pytest.mark.asyncio
async def test_extract_from_resume_case_insensitive(extractor):
    resume = "PYTHON python Python JAVASCRIPT javascript"

    result = await extractor.extract_from_resume(resume)

    programming = result["skills"]["programming_languages"]

    assert "python" in programming
    assert "javascript" in programming

    # Deduplication check
    assert programming.count("python") == 1


@pytest.mark.asyncio
async def test_extract_from_resume_duplicate_skills(extractor):
    resume = """
    Python Python Python
    React react REACT
    Docker docker
    """

    result = await extractor.extract_from_resume(resume)

    programming = result["skills"]["programming_languages"]
    web = result["skills"]["web_technologies"]
    infra = result["skills"]["cloud_infrastructure"]

    assert programming.count("python") == 1
    assert web.count("react") == 1
    assert infra.count("docker") == 1


@pytest.mark.asyncio
async def test_extract_from_resume_empty_input(extractor):
    result = await extractor.extract_from_resume("")

    assert result["skills"] == {}
    assert result["total_count"] == 0


@pytest.mark.asyncio
async def test_extract_from_resume_garbage_text(extractor):
    garbage = """
    asdkjaslkdj qweqwe zxczxc lorem ipsum banana elephant
    """

    result = await extractor.extract_from_resume(garbage)

    assert result["skills"] == {}
    assert result["total_count"] == 0


@pytest.mark.asyncio
async def test_extract_from_resume_different_resume_format(extractor):
    resume = """
    EXPERIENCE
    - Built APIs using Flask and FastAPI
    - Managed CI/CD pipelines using Jenkins
    - Used MySQL and MongoDB

    SKILLS:
    Java, Python, Docker, Kubernetes
    """

    result = await extractor.extract_from_resume(resume)

    assert "python" in result["skills"]["programming_languages"]
    assert "java" in result["skills"]["programming_languages"]
    assert "flask" in result["skills"]["web_technologies"]
    assert "fastapi" in result["skills"]["web_technologies"]
    assert "jenkins" in result["skills"]["cloud_infrastructure"]
    assert "mysql" in result["skills"]["databases"]
    assert "mongodb" in result["skills"]["databases"]


# =========================================================
# extract_from_job_description
# =========================================================

@pytest.mark.asyncio
async def test_extract_from_job_description(extractor):
    job_text = """
    Looking for a Python developer with React, AWS,
    Docker and PostgreSQL experience.
    """

    result = await extractor.extract_from_job_description(job_text)

    assert "required_skills" in result
    assert "python" in result["required_skills"]
    assert "react" in result["required_skills"]
    assert "docker" in result["required_skills"]


@pytest.mark.asyncio
async def test_extract_from_job_description_empty(extractor):
    result = await extractor.extract_from_job_description("")

    assert result["required_skills"] == []
    assert result["preferred_skills"] == []


# =========================================================
# extract_with_ai
# =========================================================

@pytest.mark.asyncio
async def test_extract_with_ai_no_api_key(extractor, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = await extractor.extract_with_ai(
        "Python React Docker"
    )

    assert "skills" in result
    assert result["total_count"] > 0


@pytest.mark.asyncio
async def test_extract_with_ai_failure_returns_basic_result(
    extractor,
    monkeypatch,
    mocker
):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    mocker.patch(
        "google.genai.Client",
        side_effect=Exception("Gemini failure")
    )

    result = await extractor.extract_with_ai(
        "Python React Docker"
    )

    # Graceful fallback
    assert "skills" in result
    assert result["total_count"] > 0


@pytest.mark.asyncio
async def test_extract_with_ai_success(extractor, monkeypatch, mocker):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    mock_response = MagicMock()
    mock_response.text = """
    Python
    React
    Docker
    Kubernetes
    """

    mock_models = MagicMock()
    mock_models.generate_content.return_value = mock_response

    mock_client = MagicMock()
    mock_client.models = mock_models

    mocker.patch(
        "google.genai.Client",
        return_value=mock_client
    )

    result = await extractor.extract_with_ai(
        "Python React Docker"
    )

    assert "ai_enhanced_skills" in result
    assert "python" in result["ai_enhanced_skills"]
    assert "react" in result["ai_enhanced_skills"]


# =========================================================
# compare_skills
# =========================================================

@pytest.mark.asyncio
async def test_compare_skills_happy_path(extractor):
    resume_skills = ["Python", "React", "Docker"]
    job_skills = ["python", "docker", "aws"]

    result = await extractor.compare_skills(
        resume_skills,
        job_skills
    )

    assert result["match_percentage"] > 0
    assert "python" in result["matched_skills"]
    assert "aws" in result["missing_skills"]


@pytest.mark.asyncio
async def test_compare_skills_empty_job(extractor):
    result = await extractor.compare_skills(
        ["python"],
        []
    )

    assert result["match_percentage"] == 0
    assert result["missing_count"] == 0


@pytest.mark.asyncio
async def test_compare_skills_case_insensitive(extractor):
    result = await extractor.compare_skills(
        ["PYTHON", "React"],
        ["python", "react"]
    )

    assert result["match_percentage"] == 100.0


# =========================================================
# get_skill_gaps
# =========================================================

@pytest.mark.asyncio
async def test_get_skill_gaps_engineer(extractor):
    result = await extractor.get_skill_gaps(
        ["python"],
        "Software Engineer"
    )

    assert result["target_role"] == "Software Engineer"
    assert result["gap_count"] >= 0
    assert isinstance(result["skills_to_learn"], list)


@pytest.mark.asyncio
async def test_get_skill_gaps_data_role(extractor):
    result = await extractor.get_skill_gaps(
        ["python"],
        "Data Analyst"
    )

    assert result["target_skill_count"] > 0


@pytest.mark.asyncio
async def test_get_skill_gaps_manager(extractor):
    result = await extractor.get_skill_gaps(
        ["communication"],
        "Engineering Manager"
    )

    assert result["target_skill_count"] > 0


# =========================================================
# Convenience wrappers
# =========================================================

@pytest.mark.asyncio
async def test_extract_resume_skills_wrapper():
    result = await extract_resume_skills(
        "Python React Docker"
    )

    assert result["total_count"] > 0


@pytest.mark.asyncio
async def test_ai_extract_skills_wrapper(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = await ai_extract_skills(
        "Python React Docker"
    )

    assert "skills" in result


@pytest.mark.asyncio
async def test_compare_resume_to_job_wrapper():
    result = await compare_resume_to_job(
        ["python", "docker"],
        "Looking for Python Docker AWS engineer"
    )

    assert "match_percentage" in result


# =========================================================
# Static data integrity
# =========================================================

def test_skill_categories_structure():
    assert isinstance(SKILL_CATEGORIES, dict)

    for category, skills in SKILL_CATEGORIES.items():
        assert isinstance(skills, list)
        assert len(skills) > 0

@pytest.mark.asyncio
async def test_extract_from_job_description_detects_nice_to_have_keyword(extractor):
    """When the job text mentions a 'nice to have' marker, the loop's break
    is hit (current implementation still marks everything as required --
    see the comment in source about needing more sophisticated parsing)."""
    job_text = "Required: Python. Bonus: experience with Kubernetes."

    result = await extractor.extract_from_job_description(job_text)

    assert "python" in result["required_skills"]
    assert result["preferred_skills"] == []