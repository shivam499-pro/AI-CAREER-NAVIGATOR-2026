from uuid import uuid4
from core.supabase_client import get_supabase


async def upload_document(
    file_bytes: bytes,
    filename: str,
    bucket: str = "documents"
) -> str:
    """
    Upload document to Supabase storage.
    """

    supabase = get_supabase()

    unique_filename = f"{uuid4()}_{filename}"

    supabase.storage.from_(bucket).upload(
        unique_filename,
        file_bytes
    )

    public_url = supabase.storage.from_(bucket).get_public_url(
        unique_filename
    )

    return public_url