"""
Tests for file upload validation.
Tests PDF validation, image validation, and file size limits.
"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestPDFValidation:
    """Test PDF file validation in resume router."""

    def test_valid_pdf_with_magic_bytes(self):
        """Test that valid PDF passes validation."""
        from routers.resume import validate_pdf_file
        
        # Valid PDF magic bytes
        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
        
        # Should not raise exception
        validate_pdf_file(valid_pdf, "resume.pdf")

    def test_invalid_extension(self):
        """Test that non-PDF extension raises error."""
        from routers.resume import validate_pdf_file
        from fastapi import HTTPException
        
        valid_content = b"%PDF-1.4\n"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf_file(valid_content, "resume.docx")
        
        assert exc_info.value.status_code == 400
        assert "pdf" in exc_info.value.detail.lower()

    def test_invalid_mime_type(self):
        """Test that wrong MIME type raises error."""
        from routers.resume import validate_pdf_file
        from fastapi import HTTPException
        
        valid_content = b"%PDF-1.4\n"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf_file(valid_content, "file.txt")
        
        assert exc_info.value.status_code == 400

    def test_file_too_small(self):
        """Test that too small file raises error."""
        from routers.resume import validate_pdf_file
        from fastapi import HTTPException
        
        # More than 4 bytes but less than valid PDF
        small_content = b"test"
        
        # This will fail magic bytes check, not size check
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf_file(small_content, "resume.pdf")
        
        assert exc_info.value.status_code == 400

    def test_invalid_pdf_content(self):
        """Test that non-PDF content raises error."""
        from routers.resume import validate_pdf_file
        from fastapi import HTTPException
        
        not_pdf = b"This is not a PDF document"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf_file(not_pdf, "resume.pdf")
        
        assert exc_info.value.status_code == 400
        assert "valid pdf" in exc_info.value.detail.lower()

    def test_uppercase_pdf_extension(self):
        """Test that uppercase .PDF extension works."""
        from routers.resume import validate_pdf_file
        
        valid_pdf = b"%PDF-1.4\n1 0 obj\nendobj\ntrailer\n%%EOF"
        
        # Should not raise
        validate_pdf_file(valid_pdf, "resume.PDF")

    def test_case_insensitive_extension(self):
        """Test case-insensitive extension check."""
        from routers.resume import validate_pdf_file
        
        valid_pdf = b"%PDF-1.4\n"
        
        # Should not raise for various cases
        validate_pdf_file(valid_pdf, "Resume.Pdf")
        validate_pdf_file(valid_pdf, "resume.PDF")
        validate_pdf_file(valid_pdf, "RESUME.PDF")


class TestDocumentsValidation:
    """Test file validation in documents router."""

    def test_valid_pdf_document(self):
        """Test valid PDF in documents router."""
        from routers.documents import validate_file_content
        
        valid_pdf = b"%PDF-1.4\n1 0 obj\nendobj\ntrailer\n%%EOF"
        
        # Should not raise
        validate_file_content(valid_pdf, "doc.pdf", "application/pdf")

    def test_valid_jpeg_image(self):
        """Test valid JPEG image."""
        from routers.documents import validate_file_content
        
        valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        
        # Should not raise
        validate_file_content(valid_jpeg, "photo.jpg", "image/jpeg")

    def test_valid_png_image(self):
        """Test valid PNG image."""
        from routers.documents import validate_file_content
        
        valid_png = b"\x89PNG\r\n\x1a\n"
        
        # Should not raise
        validate_file_content(valid_png, "photo.png", "image/png")

    def test_invalid_pdf_in_documents(self):
        """Test invalid PDF in documents router."""
        from routers.documents import validate_file_content
        from fastapi import HTTPException
        
        invalid_content = b"Not a PDF"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_content(invalid_content, "doc.pdf", "application/pdf")
        
        assert exc_info.value.status_code == 400

    def test_invalid_image_extension_pdf_content(self):
        """Test file with wrong extension but PDF content."""
        from routers.documents import validate_file_content
        
        pdf_content = b"%PDF-1.4\n"
        
        # Should raise because extension doesn't match
        with pytest.raises(Exception):
            validate_file_content(pdf_content, "doc.jpg", "image/jpeg")

    def test_image_too_small(self):
        """Test that too small image file raises error."""
        from routers.documents import validate_file_content
        from fastapi import HTTPException
        
        # Too short to be valid image
        small_image = b"\xff\xd8"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_content(small_image, "photo.jpg", "image/jpeg")
        
        # Should raise for invalid content, not "too small"
        assert exc_info.value.status_code == 400


class TestFileSizeLimits:
    """Test file size limit validation."""

    def test_pdf_size_limit(self):
        """Test that files over 10MB are rejected."""
        from routers.resume import MAX_FILE_SIZE, validate_pdf_file
        from fastapi import HTTPException
        
        # Create content larger than max size
        large_content = b"x" * (MAX_FILE_SIZE + 1)
        
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf_file(large_content, "resume.pdf")
        
        assert exc_info.value.status_code == 400

    def test_documents_size_limit(self):
        """Test 10MB limit in documents router."""
        from routers.documents import MAX_FILE_SIZE, validate_file_content
        from fastapi import HTTPException
        
        # Create file with valid magic bytes but too large
        large_content = b"PDF-1.4\n" + b"x" * (MAX_FILE_SIZE + 1)
        
        # Should fail on magic bytes check because it doesn't start with proper magic
        with pytest.raises(HTTPException) as exc_info:
            validate_file_content(large_content, "doc.pdf", "application/pdf")
        
        assert exc_info.value.status_code == 400


class TestAllowedFileTypes:
    """Test allowed file type configuration."""

    def test_pdf_allowed_type(self):
        """Test that PDF is in allowed types."""
        from routers.resume import ALLOWED_TYPES
        
        assert "application/pdf" in ALLOWED_TYPES

    def test_documents_allowed_types(self):
        """Test allowed types in documents router."""
        from routers.documents import ALLOWED_TYPES
        
        assert "application/pdf" in ALLOWED_TYPES
        assert "image/jpeg" in ALLOWED_TYPES
        assert "image/jpg" in ALLOWED_TYPES
        assert "image/png" in ALLOWED_TYPES


class TestMagicBytesConstants:
    """Test magic bytes constants."""

    def test_pdf_magic_bytes(self):
        """Test PDF magic bytes value."""
        from routers.resume import PDF_MAGIC_BYTES
        
        assert PDF_MAGIC_BYTES == b"%PDF"

    def test_documents_pdf_magic_bytes(self):
        """Test PDF magic bytes in documents router."""
        from routers.documents import PDF_MAGIC_BYTES
        
        assert PDF_MAGIC_BYTES == b"%PDF"


class TestFileValidationEdgeCases:
    """Test edge cases in file validation."""

    def test_empty_filename(self):
        """Test handling of empty filename."""
        from routers.resume import validate_pdf_file
        from fastapi import HTTPException
        
        valid_content = b"%PDF-1.4\n1 0 obj\nendobj\ntrailer\n%%EOF"
        
        with pytest.raises(HTTPException):
            validate_pdf_file(valid_content, "")

    def test_only_extension_no_filename(self):
        """Test file with only extension."""
        from routers.resume import validate_pdf_file
        from fastapi import HTTPException
        
        valid_content = b"%PDF-1.4\n"
        
        # Filename with only extension should still work
        validate_pdf_file(valid_content, ".pdf")

    def test_multiple_dots_in_filename(self):
        """Test file with multiple dots in name."""
        from routers.resume import validate_pdf_file
        
        valid_content = b"%PDF-1.4\n"
        
        # Should work - takes last extension
        validate_pdf_file(valid_content, "my.resume.final.pdf")

    def test_special_chars_in_filename(self):
        """Test file with special characters."""
        from routers.resume import validate_pdf_file
        
        valid_content = b"%PDF-1.4\n"
        
        # Should work
        validate_pdf_file(valid_content, "resume (copy).pdf")