"""
Resume Contract Tests
resumeClient.ts calls POST /upload and GET /status.
Each has a specific response shape the frontend depends on.

NOTE: routers/resume.py does NOT use the shared core.supabase_client
singleton — it defines its own module-level `supabase = create_client(url, key)`
at import time (same one-off pattern as routers/jobs.py). So every test here
patches routers.resume.supabase directly rather than using the mock_supabase
fixture that targets core.supabase_client.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from tests.integration.conftest import TEST_USER_ID, make_supabase_response


def _mock_resume_supabase():
    """A fresh MagicMock standing in for routers/resume.py's module-level
    `supabase` client instance."""
    mock = MagicMock()
    # Default table chain returns empty data.
    mock.table.return_value.select.return_value.eq.return_value \
        .execute.return_value = make_supabase_response([])
    mock.table.return_value.update.return_value.eq.return_value \
        .execute.return_value = make_supabase_response([])
    mock.table.return_value.insert.return_value \
        .execute.return_value = make_supabase_response([])
    # Storage mock.
    mock.storage.from_.return_value.upload.return_value = None
    mock.storage.from_.return_value.get_public_url.return_value = \
        "https://test.supabase.co/storage/v1/object/public/resumes/test.pdf"
    return mock


# Minimal valid PDF: magic bytes + enough structure for PyMuPDF to open it.
# fitz.open() needs a real PDF structure, so we build a minimal one.
def _make_minimal_pdf() -> bytes:
    """Build the smallest valid PDF that PyMuPDF can open and extract text from."""
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=100, height=100)
        page.insert_text((10, 50), "Python Developer with FastAPI experience")
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    except Exception:
        # Fallback: raw minimal PDF with embedded text.
        # This is a last resort if fitz can't create one.
        return (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>\nendobj\n"
            b"xref\n0 4\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n198\n%%EOF"
        )


@pytest.mark.integration
class TestResumeContract:

    # ── POST /upload — success shape ─────────────────────────────────────

    def test_upload_returns_success_and_required_fields(self, authed_client):
        """
        resumeClient.uploadResume() expects:
        { success: true, text_length: number, filename: string, resume_url: string }

        Missing fields cause the onboarding flow to silently skip resume
        confirmation and the profile to show "no resume uploaded".
        """
        pdf_bytes = _make_minimal_pdf()
        mock_sb = _mock_resume_supabase()

        with patch("routers.resume.supabase", mock_sb), \
             patch("routers.resume.extract_text_from_pdf") as mock_extract:
            mock_extract.return_value = "Python Developer with FastAPI experience"

            response = authed_client.post(
                "/api/v1/resume/upload",
                files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )

        assert response.status_code == 200, (
            f"Upload should succeed, got {response.status_code}: {response.text}"
        )
        body = response.json()

        required_fields = ["success", "text_length", "filename", "resume_url"]
        for field in required_fields:
            assert field in body, (
                f"'{field}' missing from upload response — "
                f"resumeClient.uploadResume() will break"
            )

        assert body["success"] is True
        assert body["text_length"] > 0
        assert body["filename"] == "resume.pdf"

    # ── POST /upload — non-PDF rejected with 400 ────────────────────────

    def test_upload_rejects_non_pdf_with_400(self, authed_client):
        """
        Frontend validates file type client-side, but a malicious user
        can bypass it. Backend must reject non-PDF files with 400.
        """
        response = authed_client.post(
            "/api/v1/resume/upload",
            files={"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/pdf")},
        )
        assert response.status_code == 400, (
            "Non-PDF content should be rejected with 400"
        )

    # ── POST /upload — oversized file rejected ──────────────────────────

    def test_upload_rejects_oversized_file_with_400(self, authed_client):
        """
        MAX_FILE_SIZE in resume.py is 10MB. Files above this must be
        rejected before any processing occurs.
        """
        # 11MB of valid-looking PDF header + padding.
        oversized = b"%PDF-1.4\n" + (b"X" * (11 * 1024 * 1024))

        response = authed_client.post(
            "/api/v1/resume/upload",
            files={"file": ("big_resume.pdf", io.BytesIO(oversized), "application/pdf")},
        )
        assert response.status_code == 400

    # ── POST /upload — empty PDF text rejected ──────────────────────────

    def test_upload_rejects_empty_text_extraction_with_400(self, authed_client):
        """
        If PyMuPDF extracts zero text (scanned image PDF with no OCR),
        the backend must return 400 so the frontend can prompt re-upload,
        not silently save an empty resume_text.
        """
        pdf_bytes = _make_minimal_pdf()
        mock_sb = _mock_resume_supabase()

        with patch("routers.resume.supabase", mock_sb), \
             patch("routers.resume.extract_text_from_pdf") as mock_extract:
            mock_extract.return_value = ""  # empty extraction

            response = authed_client.post(
                "/api/v1/resume/upload",
                files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )

        assert response.status_code == 400

    # ── GET /status — has resume ─────────────────────────────────────────

    def test_status_with_resume_returns_required_fields(self, authed_client):
        """
        resumeClient.getResumeStatus() expects:
        { has_resume: boolean, filename?: string, resume_url?: string }

        UploadSection.tsx shows/hides based on has_resume.
        """
        mock_sb = _mock_resume_supabase()
        mock_sb.table.return_value.select.return_value.eq.return_value \
            .execute.return_value = make_supabase_response([{
                "resume_filename": "my_resume.pdf",
                "resume_text": "Python developer with 3 years experience...",
                "resume_url": "https://test.supabase.co/storage/v1/object/public/resumes/test.pdf",
            }])

        with patch("routers.resume.supabase", mock_sb):
            response = authed_client.get("/api/v1/resume/status")

        assert response.status_code == 200
        body = response.json()

        assert "has_resume" in body, "has_resume missing — UploadSection breaks"
        assert body["has_resume"] is True
        assert body["filename"] == "my_resume.pdf"
        assert body["resume_url"] is not None

    # ── GET /status — no resume ──────────────────────────────────────────

    def test_status_without_resume_returns_has_resume_false(self, authed_client):
        """
        When the user has no resume, has_resume must be False — not missing
        or null. UploadSection renders the upload prompt based on this.
        """
        mock_sb = _mock_resume_supabase()
        mock_sb.table.return_value.select.return_value.eq.return_value \
            .execute.return_value = make_supabase_response([])

        with patch("routers.resume.supabase", mock_sb):
            response = authed_client.get("/api/v1/resume/status")

        assert response.status_code == 200
        body = response.json()
        assert body["has_resume"] is False

    # ── POST /upload — profile update and document storage ───────────────

    def test_upload_stores_in_profiles_and_user_documents(self, authed_client):
        """
        Upload must update BOTH profiles.resume_text AND insert into
        user_documents. The frontend's DocumentsPage reads from
        user_documents; losing either write silently breaks a feature.
        """
        pdf_bytes = _make_minimal_pdf()
        mock_sb = _mock_resume_supabase()

        with patch("routers.resume.supabase", mock_sb), \
             patch("routers.resume.extract_text_from_pdf") as mock_extract:
            mock_extract.return_value = "Senior Python Developer at Acme Corp"

            response = authed_client.post(
                "/api/v1/resume/upload",
                files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )

        assert response.status_code == 200

        # Verify profiles table was updated.
        mock_sb.table.assert_any_call("profiles")

        # Verify user_documents table was written to.
        mock_sb.table.assert_any_call("user_documents")

    # ── POST /upload — no file provided → 422 ───────────────────────────

    def test_upload_without_file_returns_422(self, authed_client):
        """
        FastAPI requires the `file` form field. Missing it = 422.
        Frontend should handle this edge case gracefully.
        """
        response = authed_client.post("/api/v1/resume/upload")
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body
