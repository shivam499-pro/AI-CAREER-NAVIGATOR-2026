from typing import Dict, Any

from services.document.validator import validate_document
from services.document.extractor import extract_text_from_pdf
from services.document.storage import upload_document

from services.skill_extractor import SkillExtractor
from services.document_service import save_document


async def process_document(
    *,
    user_id: str,
    filename: str,
    file_size: int,
    file_bytes: bytes,
    document_type: str
) -> Dict[str, Any]:
    """
    Main document processing pipeline.
    """

    validation = validate_document(
        filename=filename,
        file_size=file_size
    )

    if not validation["valid"]:
        return {
            "success": False,
            "error": validation["error"]
        }

    storage_url = await upload_document(
        file_bytes=file_bytes,
        filename=filename
    )

    extracted_text = ""

    if filename.lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_bytes)

    skill_extractor = SkillExtractor()

    extracted_data = await skill_extractor.extract_from_resume(
        extracted_text
    )

    document_id = save_document(
        user_id=user_id,
        document_name=filename,
        document_type=document_type,
        storage_url=storage_url,
        extracted_data=extracted_data
    )

    return {
        "success": True,
        "document_id": document_id,
        "storage_url": storage_url,
        "extracted_data": extracted_data
    }