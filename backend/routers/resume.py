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
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_resume(
    request: Request,
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload and extract text from a resume PDF.
    """
    try:
        # Validate file type
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File size must be less than 5MB"
            )
        
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
        
        # Save to Supabase profiles table
        profile_update = {
            "resume_text": text,
            "resume_filename": file.filename
        }
        
        supabase.table("profiles").update(profile_update).eq("user_id", user_id).execute()
        
        return {
            "success": True,
            "text_length": len(text),
            "filename": file.filename
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
    """
    try:
        response = supabase.table("profiles").select("resume_filename, resume_text").eq("user_id", user_id).execute()
        
        if not response.data:
            return {"has_resume": False}
        
        profile = response.data[0]
        has_resume = profile.get("resume_text") is not None and len(profile.get("resume_text", "")) > 0
        
        return {
            "has_resume": has_resume,
            "filename": profile.get("resume_filename")
        }
        
    except Exception as e:
        return {"has_resume": False, "error": str(e)}
