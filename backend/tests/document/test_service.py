from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.document.service import process_document


@pytest.mark.asyncio
async def test_process_document_happy_path():
    """
    Full successful processing flow.
    """

    with patch(
        "services.document.service.validate_document"
    ) as mock_validate, patch(
        "services.document.service.upload_document",
        new_callable=AsyncMock
    ) as mock_upload, patch(
        "services.document.service.extract_text_from_pdf"
    ) as mock_extract_pdf, patch(
        "services.document.service.SkillExtractor"
    ) as mock_skill_extractor, patch(
        "services.document.service.save_document"
    ) as mock_save:

        mock_validate.return_value = {
            "valid": True,
            "error": None
        }

        mock_upload.return_value = (
            "https://storage.supabase.co/resume.pdf"
        )

        mock_extract_pdf.return_value = (
            "Python FastAPI PostgreSQL"
        )

        mock_extractor_instance = MagicMock()

        mock_extractor_instance.extract_from_resume = AsyncMock(
            return_value={
                "skills": {
                    "programming_languages": [
                        "python"
                    ]
                }
            }
        )

        mock_skill_extractor.return_value = (
            mock_extractor_instance
        )

        mock_save.return_value = 101

        result = await process_document(
            user_id="user-1",
            filename="resume.pdf",
            file_size=1024,
            file_bytes=b"pdf-bytes",
            document_type="resume"
        )

        assert result["success"] is True
        assert result["document_id"] == 101

        assert "storage_url" in result
        assert "extracted_data" in result


@pytest.mark.asyncio
async def test_process_document_validation_failure():
    """
    Validation failure should stop pipeline.
    """

    with patch(
        "services.document.service.validate_document"
    ) as mock_validate:

        mock_validate.return_value = {
            "valid": False,
            "error": "Unsupported file type"
        }

        result = await process_document(
            user_id="user-1",
            filename="virus.exe",
            file_size=100,
            file_bytes=b"bad-file",
            document_type="resume"
        )

        assert result["success"] is False

        assert result["error"] == (
            "Unsupported file type"
        )


@pytest.mark.asyncio
async def test_process_document_storage_failure():
    """
    Storage failure should raise exception.
    """

    with patch(
        "services.document.service.validate_document"
    ) as mock_validate, patch(
        "services.document.service.upload_document",
        new_callable=AsyncMock
    ) as mock_upload:

        mock_validate.return_value = {
            "valid": True,
            "error": None
        }

        mock_upload.side_effect = Exception(
            "Supabase unavailable"
        )

        with pytest.raises(Exception):
            await process_document(
                user_id="user-1",
                filename="resume.pdf",
                file_size=1000,
                file_bytes=b"bytes",
                document_type="resume"
            )


@pytest.mark.asyncio
async def test_process_document_non_pdf_skips_extraction():
    """
    Image uploads should skip PDF extraction.
    """

    with patch(
        "services.document.service.validate_document"
    ) as mock_validate, patch(
        "services.document.service.upload_document",
        new_callable=AsyncMock
    ) as mock_upload, patch(
        "services.document.service.extract_text_from_pdf"
    ) as mock_extract_pdf, patch(
        "services.document.service.SkillExtractor"
    ) as mock_skill_extractor, patch(
        "services.document.service.save_document"
    ) as mock_save:

        mock_validate.return_value = {
            "valid": True,
            "error": None
        }

        mock_upload.return_value = (
            "https://storage.supabase.co/image.png"
        )

        mock_extractor_instance = MagicMock()

        mock_extractor_instance.extract_from_resume = AsyncMock(
            return_value={"skills": {}}
        )

        mock_skill_extractor.return_value = (
            mock_extractor_instance
        )

        mock_save.return_value = 202

        result = await process_document(
            user_id="user-1",
            filename="certificate.png",
            file_size=500,
            file_bytes=b"image",
            document_type="certificate"
        )

        assert result["success"] is True

        mock_extract_pdf.assert_not_called()


@pytest.mark.asyncio
async def test_process_document_skill_extraction_failure():
    """
    Skill extraction failure should propagate.
    """

    with patch(
        "services.document.service.validate_document"
    ) as mock_validate, patch(
        "services.document.service.upload_document",
        new_callable=AsyncMock
    ) as mock_upload, patch(
        "services.document.service.extract_text_from_pdf"
    ) as mock_extract_pdf, patch(
        "services.document.service.SkillExtractor"
    ) as mock_skill_extractor:

        mock_validate.return_value = {
            "valid": True,
            "error": None
        }

        mock_upload.return_value = (
            "https://storage.supabase.co/resume.pdf"
        )

        mock_extract_pdf.return_value = (
            "Python"
        )

        mock_extractor_instance = MagicMock()

        mock_extractor_instance.extract_from_resume = AsyncMock(
            side_effect=Exception(
                "AI extraction failure"
            )
        )

        mock_skill_extractor.return_value = (
            mock_extractor_instance
        )

        with pytest.raises(Exception):
            await process_document(
                user_id="user-1",
                filename="resume.pdf",
                file_size=100,
                file_bytes=b"pdf",
                document_type="resume"
            )