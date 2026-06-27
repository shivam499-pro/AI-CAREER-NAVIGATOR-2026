from unittest.mock import MagicMock, patch

from services.document.extractor import extract_text_from_pdf


def test_extract_text_from_pdf_happy_path():
    """
    Valid PDF should extract combined text.
    """

    mock_page_1 = MagicMock()
    mock_page_1.get_text.return_value = "Python "

    mock_page_2 = MagicMock()
    mock_page_2.get_text.return_value = "FastAPI"

    mock_document = [mock_page_1, mock_page_2]

    with patch("services.document.extractor.fitz.open") as mock_open:
        mock_open.return_value = mock_document

        result = extract_text_from_pdf(b"fake-pdf-bytes")

        assert result == "Python FastAPI"


def test_extract_text_from_pdf_empty_bytes():
    """
    Empty PDF bytes should return empty string.
    """

    result = extract_text_from_pdf(b"")

    assert result == ""


def test_extract_text_from_pdf_corrupted_pdf():
    """
    Corrupted PDF should fail gracefully.
    """

    with patch("services.document.extractor.fitz.open") as mock_open:
        mock_open.side_effect = Exception("Corrupted PDF")

        result = extract_text_from_pdf(b"invalid-pdf")

        assert result == ""


def test_extract_text_from_pdf_multiple_pages():
    """
    Multiple pages should concatenate text correctly.
    """

    mock_page_1 = MagicMock()
    mock_page_1.get_text.return_value = "Page One "

    mock_page_2 = MagicMock()
    mock_page_2.get_text.return_value = "Page Two "

    mock_page_3 = MagicMock()
    mock_page_3.get_text.return_value = "Page Three"

    mock_document = [
        mock_page_1,
        mock_page_2,
        mock_page_3
    ]

    with patch("services.document.extractor.fitz.open") as mock_open:
        mock_open.return_value = mock_document

        result = extract_text_from_pdf(b"multi-page-pdf")

        assert result == "Page One Page Two Page Three"