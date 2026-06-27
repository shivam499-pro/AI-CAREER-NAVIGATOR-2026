from pathlib import Path
from typing import Dict, Any


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg"
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_document(
    filename: str,
    file_size: int
) -> Dict[str, Any]:
    """
    Validate uploaded document.

    Args:
        filename: Uploaded file name
        file_size: File size in bytes

    Returns:
        Validation result
    """

    if not filename:
        return {
            "valid": False,
            "error": "Filename is required"
        }

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return {
            "valid": False,
            "error": "Unsupported file type"
        }

    if file_size > MAX_FILE_SIZE:
        return {
            "valid": False,
            "error": "File size exceeds limit"
        }

    return {
        "valid": True,
        "error": None
    }