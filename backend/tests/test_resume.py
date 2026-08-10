"""
Tests for routers/resume.py.

Note: this router builds its own standalone module-level `supabase` client
(same one-off pattern as ranks.py/jobs.py), constructed once at import time
via create_client(). Tests patch `routers.resume.supabase` directly.

Regression coverage: every current_user.id reference in this file was fixed
to current_user.user_id (AuthenticatedUser has no `.id` attribute — every
call to /upload and /status was broken before this fix). Tests assert the
correct user_id is threaded through rather than just checking status codes,
so a regression back to `.id` would be caught.
"""
import io
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.resume import router, MAX_FILE_SIZE, limiter
from core.middleware import get_current_user, AuthenticatedUser


# ─── Test App Setup ───────────────────────────────────────────────────────────

app = FastAPI()
app.state.limiter = limiter  # upload_resume is @limiter.limit()'d; slowapi needs this on app.state
app.include_router(router, prefix="/api/v1/resume")


def make_mock_user(user_id: str = "test-user-123") -> AuthenticatedUser:
    return AuthenticatedUser(user_id=user_id, email="test@test.com", role="user")


def override_auth(user_id: str = "test-user-123"):
    def _override():
        return make_mock_user(user_id)
    return _override


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()
    limiter.reset()


client = TestClient(app)


def make_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n%fake pdf content for testing\n"


# ─── 1. POST /upload ───────────────────────────────────────────────────────────

class TestUploadResume:
    def test_upload_unexpected_error_returns_500(self):
        """Any non-HTTPException error inside the handler is caught by the
        generic Exception handler and surfaced as a 500, not left to crash."""
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.resume.validate_pdf_file", side_effect=RuntimeError("unexpected validator crash")):
            files = {"file": ("resume.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")}
            response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 500
        assert "unexpected validator crash" in response.json()["detail"]

    def test_upload_rejects_non_pdf_content_type(self):
        app.dependency_overrides[get_current_user] = override_auth()

        files = {"file": ("resume.docx", io.BytesIO(b"not a pdf"), "application/msword")}
        response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 400
        assert "Only PDF files" in response.json()["detail"]

    def test_upload_rejects_oversized_file(self):
        app.dependency_overrides[get_current_user] = override_auth()

        oversized = b"%PDF-1.4\n" + (b"0" * (MAX_FILE_SIZE + 1))
        files = {"file": ("resume.pdf", io.BytesIO(oversized), "application/pdf")}
        response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 400
        assert "10MB" in response.json()["detail"]

    def test_upload_rejects_fake_pdf_failing_magic_bytes(self):
        """Content-Type header says PDF, but the actual bytes aren't —
        validate_pdf_file()'s real magic-byte check must catch this."""
        app.dependency_overrides[get_current_user] = override_auth()

        fake_content = b"this is not really a pdf file at all"
        files = {"file": ("resume.pdf", io.BytesIO(fake_content), "application/pdf")}
        response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 400
        assert "not a valid PDF" in response.json()["detail"]

    def test_upload_rejects_non_pdf_extension(self):
        app.dependency_overrides[get_current_user] = override_auth()

        files = {"file": ("resume.txt", io.BytesIO(make_pdf_bytes()), "application/pdf")}
        response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 400
        assert "Only .pdf files" in response.json()["detail"]

    def test_upload_extraction_failure_returns_400(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.resume.extract_text_from_pdf", side_effect=Exception("corrupt PDF stream")):
            files = {"file": ("resume.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")}
            response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 400
        assert "Failed to extract text" in response.json()["detail"]

    def test_upload_empty_extracted_text_returns_400(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.resume.extract_text_from_pdf", return_value="   "):
            files = {"file": ("resume.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")}
            response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 400
        assert "Could not extract text" in response.json()["detail"]

    def test_upload_success_full_flow(self):
        """End-to-end happy path — also the key regression test for the
        current_user.id -> current_user.user_id fix: the storage path and
        DB records must be keyed on the correct user."""
        app.dependency_overrides[get_current_user] = override_auth("user-42")

        mock_sb = MagicMock()
        mock_sb.storage.from_.return_value.get_public_url.return_value = "https://storage.test/resume.pdf"

        with patch("routers.resume.supabase", mock_sb), \
             patch("routers.resume.extract_text_from_pdf", return_value="John Doe. Python, SQL. 3 years experience."), \
             patch("routers.resume.extract_skills", return_value=["Python", "SQL"]), \
             patch("routers.resume.extract_experience", return_value=["3 years experience"]):

            files = {"file": ("resume.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")}
            response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["resume_url"] == "https://storage.test/resume.pdf"

        # Regression check: storage path must be keyed on the real user_id
        upload_call = mock_sb.storage.from_.return_value.upload.call_args
        assert "user-42/" in upload_call.kwargs["path"]

        # Regression check: profile update must filter on the real user_id
        profile_eq_call = mock_sb.table.return_value.update.return_value.eq.call_args
        assert profile_eq_call.args == ("user_id", "user-42")

        # Regression check: user_documents record must be keyed on the real user_id
        doc_insert_call = mock_sb.table.return_value.insert.call_args.args[0]
        assert doc_insert_call["user_id"] == "user-42"

    def test_upload_storage_failure_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.storage.from_.return_value.upload.side_effect = Exception("storage bucket unreachable")

        with patch("routers.resume.supabase", mock_sb), \
             patch("routers.resume.extract_text_from_pdf", return_value="Some resume text content."):

            files = {"file": ("resume.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")}
            response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 500
        assert "Failed to upload file to storage" in response.json()["detail"]

    def test_upload_profile_update_failure_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.storage.from_.return_value.get_public_url.return_value = "https://storage.test/resume.pdf"
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("db down")

        with patch("routers.resume.supabase", mock_sb), \
             patch("routers.resume.extract_text_from_pdf", return_value="Some resume text content."):

            files = {"file": ("resume.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")}
            response = client.post("/api/v1/resume/upload", files=files)

        assert response.status_code == 500
        assert "profile update failed" in response.json()["detail"]

    def test_upload_user_documents_insert_failure_is_non_fatal(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.storage.from_.return_value.get_public_url.return_value = "https://storage.test/resume.pdf"
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception("user_documents insert failed")

        with patch("routers.resume.supabase", mock_sb), \
             patch("routers.resume.extract_text_from_pdf", return_value="Some resume text content."):

            files = {"file": ("resume.pdf", io.BytesIO(make_pdf_bytes()), "application/pdf")}
            response = client.post("/api/v1/resume/upload", files=files)

        # user_documents is a secondary system — its failure must not fail the upload
        assert response.status_code == 200
        assert response.json()["success"] is True


# ─── 2. GET /status ────────────────────────────────────────────────────────────

class TestGetResumeStatus:

    def test_has_resume_true_when_text_present(self):
        app.dependency_overrides[get_current_user] = override_auth("user-42")

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "resume_filename": "resume.pdf",
            "resume_text": "Some extracted text",
            "resume_url": "https://storage.test/resume.pdf"
        }]

        with patch("routers.resume.supabase", mock_sb):
            response = client.get("/api/v1/resume/status")

        assert response.status_code == 200
        body = response.json()
        assert body["has_resume"] is True
        assert body["filename"] == "resume.pdf"

        # Regression check: must query by the real user_id
        eq_call = mock_sb.table.return_value.select.return_value.eq.call_args
        assert eq_call.args == ("user_id", "user-42")

    def test_has_resume_false_when_no_profile_row(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with patch("routers.resume.supabase", mock_sb):
            response = client.get("/api/v1/resume/status")

        assert response.status_code == 200
        assert response.json() == {"has_resume": False}

    def test_has_resume_false_when_resume_text_is_empty_string(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "resume_filename": "resume.pdf", "resume_text": "", "resume_url": None
        }]

        with patch("routers.resume.supabase", mock_sb):
            response = client.get("/api/v1/resume/status")

        assert response.status_code == 200
        assert response.json()["has_resume"] is False

    def test_has_resume_false_when_resume_text_is_none(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "resume_filename": None, "resume_text": None, "resume_url": None
        }]

        with patch("routers.resume.supabase", mock_sb):
            response = client.get("/api/v1/resume/status")

        assert response.status_code == 200
        assert response.json()["has_resume"] is False

    def test_exception_is_caught_and_returns_200_with_error_field(self):
        """This endpoint intentionally never raises — DB failures degrade to
        a 200 with has_resume=False and an error field, not a 500."""
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.resume.supabase") as mock_sb:
            mock_sb.table.side_effect = Exception("db unreachable")

            response = client.get("/api/v1/resume/status")

        assert response.status_code == 200
        body = response.json()
        assert body["has_resume"] is False
        assert "error" in body

# ─── 3. extract_text_from_pdf() — real fitz implementation ───────────────────

class TestExtractTextFromPdf:

    def test_extracts_and_concatenates_text_from_all_pages(self):
        from routers.resume import extract_text_from_pdf

        mock_page_1 = MagicMock()
        mock_page_1.get_text.return_value = "Page one text. "
        mock_page_2 = MagicMock()
        mock_page_2.get_text.return_value = "Page two text."

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)
        mock_doc.__getitem__ = MagicMock(side_effect=lambda i: [mock_page_1, mock_page_2][i])
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)

        with patch("routers.resume.fitz.open", return_value=mock_doc):
            result = extract_text_from_pdf(b"fake pdf bytes")

        assert result == "Page one text. Page two text."
        mock_page_1.get_text.assert_called_once()
        mock_page_2.get_text.assert_called_once()