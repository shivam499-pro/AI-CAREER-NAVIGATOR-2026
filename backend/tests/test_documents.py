"""
Tests for routers/documents.py — the documents/certificates HTTP layer.

Note: services/document_service.py and services/document/ already have their
own dedicated, fully-covered test suites. This file targets the router itself:
request/response handling, auth wiring, validation branches, and error paths
that only exist at the HTTP layer.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.documents import router, MAX_CERT_FILES, MAX_CERT_SIZE
from core.middleware import get_current_user, AuthenticatedUser
from services.certificate_service import CertificateResult


# ─── Test App Setup ───────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router, prefix="/api/v1/documents")


def make_mock_user(user_id: str = "test-user-123") -> AuthenticatedUser:
    """Return a real AuthenticatedUser — FastAPI type-checks dependencies."""
    return AuthenticatedUser(user_id=user_id, email="test@test.com", role="user")


def override_auth(user_id: str = "test-user-123"):
    """Returns a dependency override function for get_current_user."""
    def _override():
        return make_mock_user(user_id)
    return _override


@pytest.fixture(autouse=True)
def _reset_overrides():
    """Ensure dependency_overrides don't leak between tests."""
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def make_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n%fake pdf content for testing\n"


def make_oversized_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n" + (b"0" * (MAX_CERT_SIZE + 1))


# ─── 1. POST /upload-files ────────────────────────────────────────────────────

class TestUploadCertificates:

    def test_upload_no_files_field_returns_422(self):
        """FastAPI's own validation rejects a request with no `files` part at all
        before the handler body ever runs (files is a required File(...) param)."""
        app.dependency_overrides[get_current_user] = override_auth()

        response = client.post("/api/v1/documents/upload-files")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_empty_files_list_returns_400(self):
        """The `if not files:` guard in the handler body — only reachable by
        calling the function directly, since HTTP can't submit an empty list
        for a required File(...) field."""
        from routers.documents import upload_certificates
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await upload_certificates(
                request=MagicMock(),
                files=[],
                current_user=make_mock_user()
            )
        assert exc_info.value.status_code == 400
        assert "No files provided" in exc_info.value.detail

    def test_upload_too_many_files_returns_400(self):
        app.dependency_overrides[get_current_user] = override_auth()

        files = [
            ("files", (f"cert_{i}.pdf", make_pdf_bytes(), "application/pdf"))
            for i in range(MAX_CERT_FILES + 1)
        ]
        response = client.post("/api/v1/documents/upload-files", files=files)

        assert response.status_code == 400
        assert "Maximum" in response.json()["detail"]

    def test_upload_unsupported_file_type_recorded_as_failed(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.documents.get_supabase") as mock_get_supabase:
            mock_get_supabase.return_value = MagicMock()

            files = [("files", ("notes.txt", b"plain text", "text/plain"))]
            response = client.post("/api/v1/documents/upload-files", files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["files_failed"] == 1
        assert "Unsupported type" in body["results"][0]["error"]

    def test_upload_oversized_file_recorded_as_failed(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("routers.documents.get_supabase") as mock_get_supabase:
            mock_get_supabase.return_value = MagicMock()

            files = [("files", ("big.pdf", make_oversized_pdf_bytes(), "application/pdf"))]
            response = client.post("/api/v1/documents/upload-files", files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["files_failed"] == 1
        assert body["results"][0]["error"] == "File exceeds 5MB limit."

    def test_upload_successful_certificate(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_service = MagicMock()
        mock_service.analyze = AsyncMock(return_value=CertificateResult(
            filename="cert.pdf",
            success=True,
            data={
                "course_name": "Advanced Python",
                "provider": "Coursera",
                "skills_unlocked": ["Python", "Async Programming"],
                "certificate_weight": 7,
                "credibility": "high",
            }
        ))

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with patch("routers.documents._get_certificate_service", return_value=mock_service), \
             patch("routers.documents.get_supabase", return_value=mock_sb):

            files = [("files", ("cert.pdf", make_pdf_bytes(), "application/pdf"))]
            response = client.post("/api/v1/documents/upload-files", files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["files_processed"] == 1
        assert body["files_failed"] == 0
        assert "Python" in body["skills_added"]
        assert body["results"][0]["success"] is True
        assert body["results"][0]["extracted"]["course_name"] == "Advanced Python"

    def test_upload_db_insert_failure_recorded_as_failed(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_service = MagicMock()
        mock_service.analyze = AsyncMock(return_value=CertificateResult(
            filename="cert.pdf", success=True, data={"skills_unlocked": []}
        ))

        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception("db down")

        with patch("routers.documents._get_certificate_service", return_value=mock_service), \
             patch("routers.documents.get_supabase", return_value=mock_sb):

            files = [("files", ("cert.pdf", make_pdf_bytes(), "application/pdf"))]
            response = client.post("/api/v1/documents/upload-files", files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["files_failed"] == 1
        assert body["results"][0]["error"] == "Database save failed."

    def test_upload_ai_failure_falls_back_to_default_extraction(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_service = MagicMock()
        mock_service.analyze = AsyncMock(side_effect=Exception("gemini timeout"))

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with patch("routers.documents._get_certificate_service", return_value=mock_service), \
             patch("routers.documents.get_supabase", return_value=mock_sb):

            files = [("files", ("cert.pdf", make_pdf_bytes(), "application/pdf"))]
            response = client.post("/api/v1/documents/upload-files", files=files)

        assert response.status_code == 200
        body = response.json()
        # AI failure is non-fatal — falls back to a default record and still saves
        assert body["success"] is True
        extracted = body["results"][0]["extracted"]
        assert extracted["provider"] == "Unknown"
        assert extracted["credibility"] == "medium"
        assert extracted["summary"] == "AI analysis unavailable."

    def test_upload_merges_skills_case_insensitively(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_service = MagicMock()
        mock_service.analyze = AsyncMock(return_value=CertificateResult(
            filename="cert.pdf", success=True,
            data={"skills_unlocked": ["python", "SQL"]}
        ))

        mock_sb = MagicMock()
        # Existing profile already has "Python" (different casing) but not "SQL"
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"extra_skills": ["Python"]}
        ]

        with patch("routers.documents._get_certificate_service", return_value=mock_service), \
             patch("routers.documents.get_supabase", return_value=mock_sb):

            files = [("files", ("cert.pdf", make_pdf_bytes(), "application/pdf"))]
            response = client.post("/api/v1/documents/upload-files", files=files)

        assert response.status_code == 200
        # Assert the profile update call received a de-duplicated, merged list
        update_call = mock_sb.table.return_value.update.call_args
        merged = update_call[0][0]["extra_skills"]
        assert merged.count("Python") + merged.count("python") == 1  # no duplicate
        assert "SQL" in merged

    def test_upload_skills_profile_update_failure_is_non_fatal(self):
        app.dependency_overrides[get_current_user] = override_auth()

        mock_service = MagicMock()
        mock_service.analyze = AsyncMock(return_value=CertificateResult(
            filename="cert.pdf", success=True, data={"skills_unlocked": ["Python"]}
        ))

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("boom")

        with patch("routers.documents._get_certificate_service", return_value=mock_service), \
             patch("routers.documents.get_supabase", return_value=mock_sb):

            files = [("files", ("cert.pdf", make_pdf_bytes(), "application/pdf"))]
            response = client.post("/api/v1/documents/upload-files", files=files)

        assert response.status_code == 200
        # Profile update failing must not fail the overall request
        assert response.json()["success"] is True


# ─── 2. GET /list ─────────────────────────────────────────────────────────────

class TestListDocuments:

    def test_list_documents_no_filter(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("services.document_service.get_user_documents") as mock_get_all:
            mock_get_all.return_value = [{"id": 1, "document_name": "resume.pdf"}]

            response = client.get("/api/v1/documents/list")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["count"] == 1
        mock_get_all.assert_called_once_with("test-user-123")

    def test_list_documents_with_type_filter(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("services.document_service.get_documents_by_type") as mock_get_by_type:
            mock_get_by_type.return_value = [{"id": 2, "document_type": "certificate"}]

            response = client.get("/api/v1/documents/list?document_type=certificate")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        mock_get_by_type.assert_called_once_with("test-user-123", "certificate")

    def test_list_documents_service_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("services.document_service.get_user_documents") as mock_get_all:
            mock_get_all.side_effect = Exception("db unreachable")

            response = client.get("/api/v1/documents/list")

        assert response.status_code == 500


# ─── 3. GET /{document_id} ────────────────────────────────────────────────────

class TestGetDocument:

    def test_get_document_found_and_owned(self):
        app.dependency_overrides[get_current_user] = override_auth("owner-1")

        with patch("services.document_service.get_document_by_id") as mock_get:
            mock_get.return_value = {"id": 5, "user_id": "owner-1", "document_name": "cert.pdf"}

            response = client.get("/api/v1/documents/5")

        assert response.status_code == 200
        assert response.json()["document"]["id"] == 5

    def test_get_document_not_found_returns_404(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("services.document_service.get_document_by_id") as mock_get:
            mock_get.return_value = None

            response = client.get("/api/v1/documents/999")

        assert response.status_code == 404

    def test_get_document_owned_by_other_user_returns_403(self):
        app.dependency_overrides[get_current_user] = override_auth("requesting-user")

        with patch("services.document_service.get_document_by_id") as mock_get:
            mock_get.return_value = {"id": 5, "user_id": "someone-else"}

            response = client.get("/api/v1/documents/5")

        assert response.status_code == 403

    def test_get_document_service_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("services.document_service.get_document_by_id") as mock_get:
            mock_get.side_effect = Exception("boom")

            response = client.get("/api/v1/documents/5")

        assert response.status_code == 500


# ─── 4. DELETE /{document_id} ─────────────────────────────────────────────────

class TestDeleteDocument:

    def test_delete_document_success(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("services.document_service.delete_document") as mock_delete:
            mock_delete.return_value = True

            response = client.delete("/api/v1/documents/5")

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_document_service_returns_false_gives_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("services.document_service.delete_document") as mock_delete:
            mock_delete.return_value = False

            response = client.delete("/api/v1/documents/5")

        assert response.status_code == 500
        assert "Failed to delete" in response.json()["detail"]

    def test_delete_document_service_exception_returns_500(self):
        app.dependency_overrides[get_current_user] = override_auth()

        with patch("services.document_service.delete_document") as mock_delete:
            mock_delete.side_effect = Exception("boom")

            response = client.delete("/api/v1/documents/5")

        assert response.status_code == 500


# ─── 5. Module-level helper functions ─────────────────────────────────────────

class TestHelperFunctions:

    def test_get_certificate_service_singleton(self):
        """_get_certificate_service() builds a CertificateService once and
        reuses the same instance on every subsequent call."""
        import routers.documents as documents_module
        from services.certificate_service import CertificateService

        documents_module._certificate_service = None  # clean slate
        try:
            with patch("routers.documents.AsyncGeminiTransport.create") as mock_create:
                mock_create.return_value = MagicMock()

                first = documents_module._get_certificate_service()
                second = documents_module._get_certificate_service()

            assert isinstance(first, CertificateService)
            assert first is second               # singleton: same instance both times
            mock_create.assert_called_once()     # only constructed once, not per-call
        finally:
            documents_module._certificate_service = None  # don't leak into other tests

    def test_get_supabase_creates_client_with_env_vars(self, monkeypatch):
        """Happy path: both env vars set -> create_client(url, key)."""
        monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-service-key")

        from routers.documents import get_supabase

        with patch("routers.documents.create_client") as mock_create_client:
            mock_create_client.return_value = MagicMock()
            result = get_supabase()

        mock_create_client.assert_called_once_with(
            "https://fake.supabase.co", "fake-service-key"
        )
        assert result is mock_create_client.return_value

    def test_get_supabase_raises_when_env_vars_missing(self, monkeypatch):
        """Missing SUPABASE_URL or SUPABASE_SERVICE_KEY -> ValueError."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")

        from routers.documents import get_supabase

        with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"):
            get_supabase()