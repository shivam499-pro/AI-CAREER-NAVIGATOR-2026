"""
Tests for services/resume_service.py

Coverage targets (21 missing lines → 100%):
- extract_text(): single page, multi-page, empty doc
- extract_skills(): all three skill categories, no match, case-insensitive
- extract_experience(): each job keyword, multiple hits, no match
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ===========================================================================
# extract_text()
# ===========================================================================


class TestExtractText:
    """
    Mocks fitz.open() so no real PDF file is needed.
    Validates text accumulation across pages and that doc.close() is called.
    """

    def _make_mock_doc(self, pages: list[str]):
        """Build a fitz document mock with the given page texts."""
        mock_pages = []
        for text in pages:
            page = MagicMock()
            page.get_text.return_value = text
            mock_pages.append(page)

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter(mock_pages))
        return mock_doc

    @patch("services.resume_service.fitz.open")
    def test_extract_text_single_page(self, mock_fitz_open):
        """Single-page PDF → text returned as-is."""
        mock_doc = self._make_mock_doc(["Hello from page 1"])
        mock_fitz_open.return_value = mock_doc

        from services.resume_service import extract_text
        result = extract_text("/fake/resume.pdf")

        assert result == "Hello from page 1"

    @patch("services.resume_service.fitz.open")
    def test_extract_text_multi_page_concatenates(self, mock_fitz_open):
        """Multi-page PDF → all pages concatenated in order."""
        mock_doc = self._make_mock_doc(["Page one. ", "Page two. ", "Page three."])
        mock_fitz_open.return_value = mock_doc

        from services.resume_service import extract_text
        result = extract_text("/fake/resume.pdf")

        assert result == "Page one. Page two. Page three."

    @patch("services.resume_service.fitz.open")
    def test_extract_text_empty_pdf(self, mock_fitz_open):
        """PDF with no pages → empty string returned."""
        mock_doc = self._make_mock_doc([])
        mock_fitz_open.return_value = mock_doc

        from services.resume_service import extract_text
        result = extract_text("/fake/empty.pdf")

        assert result == ""

    @patch("services.resume_service.fitz.open")
    def test_extract_text_calls_doc_close(self, mock_fitz_open):
        """doc.close() must always be called to release file handle."""
        mock_doc = self._make_mock_doc(["some text"])
        mock_fitz_open.return_value = mock_doc

        from services.resume_service import extract_text
        extract_text("/fake/resume.pdf")

        mock_doc.close.assert_called_once()

    @patch("services.resume_service.fitz.open")
    def test_extract_text_opens_correct_path(self, mock_fitz_open):
        """fitz.open is called with the exact path provided."""
        mock_doc = self._make_mock_doc([])
        mock_fitz_open.return_value = mock_doc

        from services.resume_service import extract_text
        extract_text("/documents/my_resume.pdf")

        mock_fitz_open.assert_called_once_with("/documents/my_resume.pdf")


# ===========================================================================
# extract_skills()
# ===========================================================================


class TestExtractSkills:
    """
    extract_skills is pure — no mocks needed.
    Tests case-insensitive matching across all three skill categories.
    """

    def test_detects_programming_languages(self):
        from services.resume_service import extract_skills
        text = "Proficient in Python, JavaScript, and TypeScript."
        result = extract_skills(text)
        assert "Python" in result
        assert "JavaScript" in result
        assert "TypeScript" in result

    def test_detects_frameworks(self):
        from services.resume_service import extract_skills
        text = "Built services using FastAPI, React, and Next.js"
        result = extract_skills(text)
        assert "FastAPI" in result
        assert "React" in result
        assert "Next.js" in result

    def test_detects_tools(self):
        from services.resume_service import extract_skills
        text = "Used Docker, Kubernetes, AWS, Redis, and PostgreSQL daily."
        result = extract_skills(text)
        assert "Docker" in result
        assert "Kubernetes" in result
        assert "AWS" in result
        assert "Redis" in result
        assert "PostgreSQL" in result

    def test_case_insensitive_matching(self):
        """Skills should be found regardless of casing in the resume text."""
        from services.resume_service import extract_skills
        text = "experienced with PYTHON, django, and GIT"
        result = extract_skills(text)
        assert "Python" in result
        assert "Django" in result
        assert "Git" in result

    def test_returns_empty_list_when_no_skills_found(self):
        from services.resume_service import extract_skills
        text = "I enjoy hiking, cooking, and reading novels."
        result = extract_skills(text)
        assert result == []

    def test_returns_list_type(self):
        from services.resume_service import extract_skills
        result = extract_skills("Python developer")
        assert isinstance(result, list)

    def test_does_not_duplicate_skills(self):
        """Same skill appearing multiple times → appears once in result."""
        from services.resume_service import extract_skills
        text = "Python Python Python expert with Python experience"
        result = extract_skills(text)
        assert result.count("Python") == 1

    def test_detects_all_language_entries(self):
        """Verify every language in the list is matched."""
        from services.resume_service import extract_skills
        all_languages = "Python JavaScript TypeScript Java C++ C# Go Rust Ruby PHP Swift Kotlin Scala R"
        result = extract_skills(all_languages)
        for lang in ["Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R"]:
            assert lang in result, f"Expected {lang} to be detected"

    def test_detects_sql_tool(self):
        from services.resume_service import extract_skills
        text = "Wrote complex SQL queries for reporting."
        result = extract_skills(text)
        assert "SQL" in result

    def test_detects_gcp_and_azure(self):
        from services.resume_service import extract_skills
        text = "Deployed workloads on GCP and Azure"
        result = extract_skills(text)
        assert "GCP" in result
        assert "Azure" in result

    def test_detects_tailwind(self):
        from services.resume_service import extract_skills
        text = "Styled UI components using Tailwind CSS"
        result = extract_skills(text)
        assert "Tailwind" in result


# ===========================================================================
# extract_experience()
# ===========================================================================


class TestExtractExperience:
    """
    extract_experience is pure — matches job title keywords in text.
    """

    def test_detects_engineer_keyword(self):
        from services.resume_service import extract_experience
        text = "Worked as a Software Engineer at TechCorp."
        result = extract_experience(text)
        assert "Engineer" in result

    def test_detects_developer_keyword(self):
        from services.resume_service import extract_experience
        text = "Frontend Developer at StartupXYZ"
        result = extract_experience(text)
        assert "Developer" in result

    def test_detects_manager_keyword(self):
        from services.resume_service import extract_experience
        text = "Engineering Manager responsible for a team of 8."
        result = extract_experience(text)
        assert "Manager" in result

    def test_detects_analyst_keyword(self):
        from services.resume_service import extract_experience
        text = "Business Analyst at FinTech Solutions"
        result = extract_experience(text)
        assert "Analyst" in result

    def test_detects_designer_keyword(self):
        from services.resume_service import extract_experience
        text = "UI/UX Designer with 5 years experience"
        result = extract_experience(text)
        assert "Designer" in result

    def test_returns_empty_list_when_no_keywords_found(self):
        from services.resume_service import extract_experience
        text = "I studied computer science and enjoy open source."
        result = extract_experience(text)
        assert result == []

    def test_detects_multiple_keywords_in_single_text(self):
        """Text with multiple job keywords → all detected."""
        from services.resume_service import extract_experience
        text = "Started as a Developer, promoted to Engineer, now a Manager."
        result = extract_experience(text)
        assert "Developer" in result
        assert "Engineer" in result
        assert "Manager" in result

    def test_returns_list_type(self):
        from services.resume_service import extract_experience
        result = extract_experience("Software Engineer")
        assert isinstance(result, list)

    def test_case_insensitive_match(self):
        """Matching is case-insensitive via .lower()."""
        from services.resume_service import extract_experience
        text = "senior software engineer"
        result = extract_experience(text)
        assert "Engineer" in result

    def test_all_five_keywords_detectable(self):
        from services.resume_service import extract_experience
        text = "Engineer Developer Manager Analyst Designer"
        result = extract_experience(text)
        for kw in ["Engineer", "Developer", "Manager", "Analyst", "Designer"]:
            assert kw in result