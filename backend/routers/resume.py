"""
Resume Router
Handles resume PDF upload and text extraction
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from supabase import create_client
import os
import uuid
import fitz  # PyMuPDF
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Allowed file types
ALLOWED_TYPES = ["application/pdf"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Supabase Storage bucket name for resumes
RESUME_BUCKET = "resumes"

# PDF magic bytes (first 4 bytes of a valid PDF)
PDF_MAGIC_BYTES = b"%PDF"


def validate_pdf_file(content: bytes, filename: str) -> None:
    """
    Validate that the file is a real PDF using magic bytes.
    Raises HTTPException with clear error message if validation fails.
    """
    # Validate file extension
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .pdf files are allowed."
        )
    
    # Validate MIME type
    content_type = filename.lower().split(".")[-1]
    if content_type != "pdf":
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are allowed."
        )
    
    # Validate magic bytes (PDF files start with %PDF)
    if len(content) < 4:
        raise HTTPException(
            status_code=400,
            detail="Invalid file. File is too small to be a valid PDF."
        )
    
    if not content.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=400,
            detail="Invalid file content. The file is not a valid PDF document."
        )


def upload_to_supabase_storage(file_content: bytes, filename: str, user_id: str) -> str:
    """
    Upload file to Supabase Storage and return the public URL.
    """
    # Generate unique filename to avoid conflicts
    ext = filename.split(".")[-1] if "." in filename else "pdf"
    unique_filename = f"{user_id}/{uuid.uuid4()}.{ext}"
    
    try:
        # Upload to Supabase Storage
        supabase.storage.from_(RESUME_BUCKET).upload(
            path=unique_filename,
            file=file_content,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true"
            }
        )
        
        # Get public URL
        public_url = supabase.storage.from_(RESUME_BUCKET).get_public_url(unique_filename)
        return public_url
        
    except Exception as e:
        print(f"Supabase Storage upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file to storage: {str(e)}"
        )


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_resume(
    request: Request,
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload and extract text from a resume PDF.
    Stores file in Supabase Storage and extracts text for analysis.
    """
    try:
        # Validate file extension and MIME type
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF files are allowed."
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size (10MB limit)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File size must be less than 10MB"
            )
        
        # Validate PDF magic bytes (must be a real PDF)
        validate_pdf_file(content, file.filename)
        
        # Extract text from PDF using PyMuPDF
        try:
            text = extract_text_from_pdf(content)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract text from PDF: {str(e)}"
            )
        
        if not text or len(text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the PDF"
            )
        
        # Upload file to Supabase Storage
        resume_url = upload_to_supabase_storage(content, file.filename, user_id)
        
        # Save to Supabase profiles table (both text and URL)
        profile_update = {
            "resume_text": text,
            "resume_filename": file.filename,
            "resume_url": resume_url
        }
        
        supabase.table("profiles").update(profile_update).eq("user_id", user_id).execute()
        
        return {
            "success": True,
            "text_length": len(text),
            "filename": file.filename,
            "resume_url": resume_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from PDF using PyMuPDF (fitz).
    """
    text = ""
    
    # Open PDF from bytes
    with fitz.open(stream=pdf_content, filetype="pdf") as doc:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += page.get_text()
    
    return text.strip()


@router.get("/status/{user_id}")
async def get_resume_status(user_id: str):
    """
    Check if user has uploaded a resume.
    Returns resume status including the URL if available.
    """
    try:
        response = supabase.table("profiles").select("resume_filename, resume_text, resume_url").eq("user_id", user_id).execute()
        
        if not response.data:
            return {"has_resume": False}
        
        profile = response.data[0]
        has_resume = profile.get("resume_text") is not None and len(profile.get("resume_text", "")) > 0
        
        return {
            "has_resume": has_resume,
            "filename": profile.get("resume_filename"),
            "resume_url": profile.get("resume_url")
        }
        
    except Exception as e:
        return {"has_resume": False, "error": str(e)}
