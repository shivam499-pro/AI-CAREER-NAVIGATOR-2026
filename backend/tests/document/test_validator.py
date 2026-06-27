from services.document.validator import validate_document

def test_validate_document_valid_pdf():
    result = validate_document(
        filename="resume.pdf",
        file_size=1024
    )

    assert result["valid"] is True
    assert result["error"] is None

def test_validate_document_valid_image():
    result = validate_document(
        filename="photo.png",
        file_size=2048
    )

    assert result["valid"] is True

def test_validate_document_invalid_extension():
    result = validate_document(
        filename="malware.exe",
        file_size=1024
    )

    assert result["valid"] is False
    assert result["error"] == "Unsupported file type"


from services.document.validator import MAX_FILE_SIZE


def test_validate_document_oversized():
    result = validate_document(
        filename="large.pdf",
        file_size=MAX_FILE_SIZE + 1
    )

    assert result["valid"] is False
    assert result["error"] == "File size exceeds limit"

def test_validate_document_empty_filename():
    result = validate_document(
        filename="",
        file_size=100
    )

    assert result["valid"] is False
    assert result["error"] == "Filename is required"

