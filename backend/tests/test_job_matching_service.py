import pytest

from services.job_matching_service import (
    match_jobs,
    calculate_match_score,
    calculate_skill_match_score,
    calculate_experience_match,
    extract_skills_from_job,
    normalize_user_skills,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def user_profile_full():
    return {
        "profile": {
            "current_tech_stack": ["Python", "FastAPI", "PostgreSQL"],
            "extra_skills": ["Docker", "Git"],
            "career_goal": "Backend Developer"
        },
        "analysis": {
            "strengths": ["Python backend development"],
            "skill_gaps": ["aws"]
        },
        "experience_level": "mid"
    }


@pytest.fixture
def user_profile_partial():
    return {
        "profile": {
            "current_tech_stack": ["Python"],
            "extra_skills": []
        },
        "analysis": {},
        "experience_level": "entry"
    }


@pytest.fixture
def user_profile_empty():
    return {
        "profile": {},
        "analysis": {},
        "experience_level": None
    }


@pytest.fixture
def jobs_sample():
    return [
        {
            "id": "job_1",
            "title": "Backend Engineer Python FastAPI",
            "description": "We use Python, FastAPI, PostgreSQL, Docker",
            "location": "remote",
            "salary": 120000,
            "remote": True
        },
        {
            "id": "job_2",
            "title": "Frontend Engineer React",
            "description": "React, JavaScript, CSS, HTML",
            "location": "chennai",
            "salary": 90000,
            "remote": False
        },
        {
            "id": "job_3",
            "title": "DevOps Engineer AWS Docker Kubernetes",
            "description": "AWS, Docker, Kubernetes, CI/CD",
            "location": "bangalore",
            "salary": 150000,
            "remote": True
        }
    ]


# =============================================================================
# UNIT TESTS - CORE LOGIC
# =============================================================================

def test_extract_skills_from_job():
    desc = "We use Python, FastAPI, PostgreSQL and Docker"
    skills = extract_skills_from_job(desc)

    assert "python" in skills
    assert "fastapi" in skills
    assert "postgresql" in skills
    assert "docker" in skills


def test_normalize_user_skills():
    profile = {
        "current_tech_stack": ["Python", "React"],
        "extra_skills": ["Docker"]
    }
    analysis = {
        "strengths": ["FastAPI backend"]
    }

    skills = normalize_user_skills(profile, analysis)

    assert "python" in skills
    assert "react" in skills
    assert "docker" in skills


def test_skill_match_full_match():
    user_skills = ["python", "fastapi", "postgresql"]
    job_skills = ["python", "fastapi", "postgresql"]

    score = calculate_skill_match_score(user_skills, job_skills)

    assert score == 100.0


def test_skill_match_partial():
    user_skills = ["python"]
    job_skills = ["python", "fastapi", "postgresql"]

    score = calculate_skill_match_score(user_skills, job_skills)

    assert 0 < score < 100


def test_skill_match_none():
    user_skills = ["java"]
    job_skills = ["python", "fastapi"]

    score = calculate_skill_match_score(user_skills, job_skills)

    assert score == 0.0


def test_experience_match_equal():
    assert calculate_experience_match("mid", "mid") == 100.0


def test_experience_match_underqualified():
    assert calculate_experience_match("entry", "senior") == 80.0


def test_experience_match_overqualified():
    assert calculate_experience_match("senior", "entry") == 60.0


def test_user_skills_dict_format_branch():
    from services.job_matching_service import normalize_user_skills

    profile = {
        "current_tech_stack": {
            "backend": ["Python", "FastAPI"],
            "db": ["PostgreSQL"]
        }
    }

    skills = normalize_user_skills(profile, None)

    assert "python" in skills
    assert "fastapi" in skills
    assert "postgresql" in skills



def test_strengths_extracts_tech_keywords():
    from services.job_matching_service import normalize_user_skills

    profile = {}
    analysis = {
        "strengths": ["Built scalable React + NodeJS backend systems"]
    }

    skills = normalize_user_skills(profile, analysis)

    assert "react" in skills
    assert "nodejs" in skills or "node.js" in skills

def test_career_goal_mismatch_path():
    from services.job_matching_service import calculate_career_goal_match

    profile = {
        "career_goal": "Frontend Developer"
    }

    score = calculate_career_goal_match(profile, "DevOps Engineer AWS")

    assert score in [0.5, 1.0]

def test_empty_job_skills_returns_neutral():
    from services.job_matching_service import calculate_skill_match_score

    user_skills = ["python", "docker"]
    job_skills = []

    score = calculate_skill_match_score(user_skills, job_skills)

    assert score == 50.0
    
# =============================================================================
# INTEGRATION TESTS - MATCH ENGINE
# =============================================================================
def test_skill_gaps_dict_branch():
    from services.job_matching_service import calculate_match_score

    user = {
        "profile": {"current_tech_stack": ["python"]},
        "analysis": {
            "skill_gaps": {
                "backend": ["aws", "docker"]
            }
        },
        "experience_level": "mid"
    }

    job = {
        "title": "Backend Engineer AWS Docker",
        "description": "AWS Docker required"
    }

    result = calculate_match_score(user, job)

    assert "match_score" in result
    assert result["match_score"] >= 0


def test_match_jobs_empty_jobs(user_profile_full):
    result = match_jobs(user_profile_full, [])
    assert result == []


def test_match_jobs_returns_sorted(user_profile_full, jobs_sample):
    result = match_jobs(user_profile_full, jobs_sample)

    scores = [job["match_score"] for job in result]

    assert scores == sorted(scores, reverse=True)


def test_full_profile_matches_backend_best(user_profile_full, jobs_sample):
    result = match_jobs(user_profile_full, jobs_sample)

    top_job = result[0]

    assert top_job["id"] == "job_1"
    assert top_job["match_score"] > 60


def test_partial_profile_lower_scores(user_profile_partial, jobs_sample):
    result = match_jobs(user_profile_partial, jobs_sample)

    for job in result:
        assert "match_score" in job
        assert 0 <= job["match_score"] <= 100


def test_empty_user_profile_no_crash(user_profile_empty, jobs_sample):
    result = match_jobs(user_profile_empty, jobs_sample)

    assert isinstance(result, list)
    assert len(result) == len(jobs_sample)

def test_null_analysis_and_profile_paths():
    from services.job_matching_service import match_jobs

    user = {
        "profile": None,
        "analysis": None,
        "experience_level": None
    }

    jobs = [
        {
            "id": "job_x",
            "title": "Python Engineer",
            "description": "Python Docker AWS"
        }
    ]

    result = match_jobs(user, jobs)

    assert len(result) == 1
    assert "match_score" in result[0]
# =============================================================================
# EDGE CASES
# =============================================================================

def test_missing_user_skills_safe_handling(jobs_sample):
    user = {
        "profile": None,
        "analysis": None,
        "experience_level": None
    }

    result = match_jobs(user, jobs_sample)

    assert len(result) == 3
    assert all("match_score" in job for job in result)


def test_job_without_description(jobs_sample):
    user = {
        "profile": {"current_tech_stack": ["python"]},
        "analysis": {},
        "experience_level": "mid"
    }

    jobs = [
        {
            "id": "job_x",
            "title": "Python Engineer",
            "location": "remote"
        }
    ]

    result = match_jobs(user, jobs)

    assert result[0]["match_score"] >= 0


def test_missing_job_skills_defaults_behavior():
    user = {
        "profile": {"current_tech_stack": ["python"]},
        "analysis": {},
        "experience_level": "mid"
    }

    jobs = [
        {
            "id": "job_x",
            "title": "Engineer",
            "description": "",
        }
    ]

    result = match_jobs(user, jobs)

    assert result[0]["match_score"] >= 0


# =============================================================================
# LIMIT BEHAVIOR
# =============================================================================

def test_job_limit_applied(user_profile_full, jobs_sample):
    result = match_jobs(user_profile_full, jobs_sample, limit=2)

    assert len(result) == 2