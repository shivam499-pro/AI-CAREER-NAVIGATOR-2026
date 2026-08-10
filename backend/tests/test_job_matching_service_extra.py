"""
Additional tests for services/job_matching_service.py filling in coverage
gaps left by tests/test_job_matching_service.py:

- normalize_user_skills: tech_stack dict whose value is a plain string
- determine_experience_level: "senior" and "entry" branches
- calculate_career_goal_match: TECH_SKILLS fallback loop (match and no-match)
- calculate_skill_gap_penalty: no job_skills, and no missing skills
- get_top_skills_missing: previously fully untested
- get_recommended_improvements: previously fully untested
"""
from services.job_matching_service import (
    normalize_user_skills,
    determine_experience_level,
    calculate_career_goal_match,
    calculate_skill_gap_penalty,
    get_top_skills_missing,
    get_recommended_improvements,
)


# ─── normalize_user_skills: tech_stack dict with string value ──────────────

def test_normalize_user_skills_handles_dict_tech_stack_with_string_value():
    profile = {"current_tech_stack": {"primary_language": "Python"}}

    skills = normalize_user_skills(profile, analysis=None)

    assert "python" in skills


def test_normalize_user_skills_handles_dict_tech_stack_mixed_list_and_string():
    profile = {
        "current_tech_stack": {
            "languages": ["Python", "Go"],
            "primary_language": "Rust",
        }
    }

    skills = normalize_user_skills(profile, analysis=None)

    assert "python" in skills
    assert "go" in skills
    assert "rust" in skills


# ─── determine_experience_level: senior / entry branches ──────────────────

def test_determine_experience_level_detects_senior_title():
    level = determine_experience_level("Senior Backend Engineer")

    assert level == "senior"


def test_determine_experience_level_detects_entry_title():
    level = determine_experience_level("Junior Software Developer")

    assert level == "entry"


def test_determine_experience_level_defaults_to_mid_when_no_keywords_match():
    level = determine_experience_level("Software Engineer")

    assert level == "mid"


# ─── calculate_career_goal_match: TECH_SKILLS fallback loop ────────────────

def test_career_goal_match_falls_back_to_tech_skill_overlap():
    """career_goal doesn't map to any CAREER_GOAL_KEYWORDS category, but a
    raw tech-skill token appears in both the goal and the job title."""
    profile = {"career_goal": "Rust developer"}

    score = calculate_career_goal_match(profile, "Rust Systems Engineer")

    assert score == 1.0


def test_career_goal_match_returns_neutral_when_no_category_or_skill_overlap():
    # Chosen to avoid incidentally matching any CAREER_GOAL_KEYWORDS category
    # AND to avoid the job title containing any TECH_SKILLS substring
    # (including single-character entries like "r").
    profile = {"career_goal": "human resources management"}

    score = calculate_career_goal_match(profile, "Executive Assistant")

    assert score == 0.5


# ─── calculate_skill_gap_penalty: no requirements / no missing skills ──────

def test_skill_gap_penalty_is_zero_when_job_has_no_required_skills():
    penalty = calculate_skill_gap_penalty(job_skills=[], user_skills=["python"])

    assert penalty == 0.0


def test_skill_gap_penalty_is_zero_when_user_has_all_required_skills():
    penalty = calculate_skill_gap_penalty(
        job_skills=["python", "sql"], user_skills=["python", "sql", "docker"]
    )

    assert penalty == 0.0


# ─── get_top_skills_missing ─────────────────────────────────────────────────

def test_get_top_skills_missing_returns_only_missing_skills():
    result = get_top_skills_missing(
        user_skills=["python"], job_skills=["python", "docker", "kubernetes"]
    )

    assert set(result) == {"docker", "kubernetes"}


def test_get_top_skills_missing_prioritizes_important_skills_first():
    result = get_top_skills_missing(
        user_skills=[], job_skills=["kubernetes", "python", "some_obscure_tool"], n=5
    )

    # "python" is in the `important` set and should be prioritized ahead of
    # skills that aren't.
    assert result[0] == "python"


def test_get_top_skills_missing_respects_the_limit_n():
    result = get_top_skills_missing(
        user_skills=[], job_skills=["a", "b", "c", "d", "e"], n=2
    )

    assert len(result) == 2


def test_get_top_skills_missing_returns_empty_when_user_has_everything():
    result = get_top_skills_missing(user_skills=["python", "sql"], job_skills=["python", "sql"])

    assert result == []


# ─── get_recommended_improvements ───────────────────────────────────────────

def test_get_recommended_improvements_links_known_skill_resources():
    matched_job = {"missing_skills": ["python", "docker"]}

    result = get_recommended_improvements(matched_job)

    assert any("python" in r.lower() and "python.org" in r for r in result)
    assert any("docker" in r.lower() and "docs.docker.com" in r for r in result)


def test_get_recommended_improvements_falls_back_to_generic_practice_message():
    matched_job = {"missing_skills": ["some_niche_tool"]}

    result = get_recommended_improvements(matched_job)

    assert result == ["Practice some_niche_tool through projects"]


def test_get_recommended_improvements_only_considers_first_three_missing_skills():
    matched_job = {"missing_skills": ["python", "docker", "sql", "kubernetes", "git"]}

    result = get_recommended_improvements(matched_job)

    assert len(result) == 3


def test_get_recommended_improvements_returns_empty_list_when_no_missing_skills():
    result = get_recommended_improvements({"missing_skills": []})

    assert result == []


def test_get_recommended_improvements_handles_missing_key_gracefully():
    result = get_recommended_improvements({})

    assert result == []