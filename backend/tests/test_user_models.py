from datetime import datetime

from models.user import UserProfile, ProfileInput


def test_user_profile_creation():
    profile = UserProfile(
        id="123",
        email="test@example.com",
        created_at=datetime.now(),
        github_url="https://github.com/test",
        leetcode_username="leetcode_user",
        linkedin_url="https://linkedin.com/in/test",
        resume_url="resume.pdf",
        analysis_complete=True,
    )

    assert profile.id == "123"
    assert profile.email == "test@example.com"
    assert profile.analysis_complete is True


def test_user_profile_defaults():
    profile = UserProfile(
        id="123",
        email="test@example.com",
        created_at=datetime.now(),
    )

    assert profile.analysis_complete is False


def test_user_profile_optional_fields():
    profile = UserProfile(
        id="123",
        email="test@example.com",
        created_at=datetime.now(),
    )

    assert profile.github_url is None
    assert profile.leetcode_username is None
    assert profile.linkedin_url is None
    assert profile.resume_url is None


def test_profile_input_creation():
    profile = ProfileInput(
        github_url="https://github.com/test",
        leetcode_username="user",
        linkedin_url="https://linkedin.com/in/test",
    )

    assert profile.github_url is not None
    assert profile.leetcode_username == "user"
    assert profile.linkedin_url is not None


def test_validate_github_url_valid():
    profile = ProfileInput(
        github_url="https://github.com/test"
    )

    assert profile.validate_github_url() is True


def test_validate_github_url_invalid():
    profile = ProfileInput(
        github_url="https://google.com/test"
    )

    assert profile.validate_github_url() is False


def test_validate_github_url_none():
    profile = ProfileInput()

    assert profile.validate_github_url() is True


def test_validate_linkedin_url_all_branches():
    valid = ProfileInput(
        linkedin_url="https://linkedin.com/in/test"
    )
    assert valid.validate_linkedin_url() is True

    invalid = ProfileInput(
        linkedin_url="https://google.com/profile"
    )
    assert invalid.validate_linkedin_url() is False

    empty = ProfileInput()
    assert empty.validate_linkedin_url() is True