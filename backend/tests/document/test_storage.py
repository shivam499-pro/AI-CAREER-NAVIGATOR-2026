from unittest.mock import MagicMock, patch

import pytest

from services.document.storage import upload_document


@pytest.mark.asyncio
async def test_upload_document_success():
    """
    Successful upload should return public URL.
    """

    mock_bucket = MagicMock()

    mock_bucket.get_public_url.return_value = (
        "https://supabase.com/storage/test.pdf"
    )

    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_bucket

    mock_supabase = MagicMock()
    mock_supabase.storage = mock_storage

    with patch(
        "services.document.storage.get_supabase",
        return_value=mock_supabase
    ):

        result = await upload_document(
            file_bytes=b"fake-bytes",
            filename="resume.pdf"
        )

        assert result == (
            "https://supabase.com/storage/test.pdf"
        )

        mock_bucket.upload.assert_called_once()
        mock_bucket.get_public_url.assert_called_once()


@pytest.mark.asyncio
async def test_upload_document_failure():
    """
    Upload failure should raise exception.
    """

    mock_bucket = MagicMock()

    mock_bucket.upload.side_effect = Exception(
        "Storage failure"
    )

    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_bucket

    mock_supabase = MagicMock()
    mock_supabase.storage = mock_storage

    with patch(
        "services.document.storage.get_supabase",
        return_value=mock_supabase
    ):

        with pytest.raises(Exception):
            await upload_document(
                file_bytes=b"bad-file",
                filename="resume.pdf"
            )


@pytest.mark.asyncio
async def test_upload_document_generates_unique_filename():
    """
    Upload should generate unique filename.
    """

    mock_bucket = MagicMock()

    mock_bucket.get_public_url.return_value = (
        "https://supabase.com/storage/file.pdf"
    )

    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_bucket

    mock_supabase = MagicMock()
    mock_supabase.storage = mock_storage

    with patch(
        "services.document.storage.get_supabase",
        return_value=mock_supabase
    ):

        await upload_document(
            file_bytes=b"file",
            filename="resume.pdf"
        )

        upload_call = mock_bucket.upload.call_args

        uploaded_filename = upload_call[0][0]

        assert uploaded_filename.endswith(
            "_resume.pdf"
        )