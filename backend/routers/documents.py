"""
Documents Router
Handles multi-document upload and AI extraction via Gemini multimodal API.

Supabase migration (run once in SQL Editor):
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS documents_data jsonb DEFAULT '{}';
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from supabase import create_client
from google import genai
from typing import List
import os
import json
import re
import base64
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

# Initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client_genai = genai.Client(api_key=GEMINI_API_KEY)

# Allowed file types
ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "image/jpeg": "jpeg",
    "image/jpg": "jpg",
    "image/png": "png",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_FILES = 10

# PDF magic bytes (first 4 bytes of a valid PDF)
PDF_MAGIC_BYTES = b"%PDF"


def validate_file_content(content: bytes, filename: str, content_type: str) -> None:
    """
    Validate file content using magic bytes.
    Raises HTTPException with clear error message if validation fails.
    """
    filename_lower = filename.lower()
    
    # Validate file extension matches content type for PDF
    if content_type == "application/pdf":
        if not filename_lower.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. File '{filename}' must have .pdf extension."
            )
        
        # Validate magic bytes for PDF
        if len(content) < 4:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file '{filename}'. File is too small to be a valid PDF."
            )
        
        if not content.startswith(PDF_MAGIC_BYTES):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file content. File '{filename}' is not a valid PDF document."
            )
    
    # Validate image files have image magic bytes
    elif content_type in ["image/jpeg", "image/jpg", "image/png"]:
        expected_magic = {
            "image/jpeg": b"\xff\xd8\xff",
            "image/jpg": b"\xff\xd8\xff",
            "image/png": b"\x89PNG"
        }
        magic = expected_magic.get(content_type)
        if magic and not content.startswith(magic):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file content. File '{filename}' is not a valid {content_type.split('/')[1].upper()} image."
            )

EXTRACTION_PROMPT = """You are analyzing career documents for a student/professional.

Analyze the document and extract ALL relevant information. Determine the document type (certificate, resume, cover_letter, or other).

Return ONLY a valid JSON object with this exact structure:
{
  "document_type": "certificate/resume/cover_letter/other",
  "skills": ["skill1", "skill2"],
  "education": [{"institution": "name", "degree": "degree name", "field": "field of study", "year": "year"}],
  "experience": [{"company": "company name", "role": "job title", "duration": "duration", "description": "job description"}],
  "certifications": [{"name": "certificate name", "issuer": "organization", "date": "date earned"}],
  "projects": [{"name": "project name", "description": "project description", "technologies": ["tech1"]}],
  "achievements": ["achievement1", "achievement2"],
  "summary": "brief summary of the document content"
}

If any field has no data, use an empty array or empty string.
Do not return anything else."""


def _clean_json(text: str) -> str:
    """Strip markdown code fences and extract the JSON object."""
    text = text.strip()
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    if text.startswith('{'):
        depth = 0
        for i, c in enumerate(text):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            if depth == 0:
                text = text[:i + 1]
                break
    return text.strip()


def _get_default_extracted_data() -> dict:
    """Return default extracted data structure when extraction fails."""
    return {
        "document_type": "other",
        "skills": [],
        "education": [],
        "experience": [],
        "certifications": [],
        "projects": [],
        "achievements": [],
        "summary": ""
    }


def _detect_document_type(filename: str, extracted_data: dict) -> str:
    """Detect document type based on filename or Gemini output."""
    filename_lower = filename.lower()
    
    # First check filename
    if "certificate" in filename_lower or "cert" in filename_lower:
        return "certificate"
    elif "resume" in filename_lower or "cv" in filename_lower:
        return "resume"
    elif "cover" in filename_lower:
        return "cover_letter"
    
    # Fallback to Gemini's detected type
    gemini_type = extracted_data.get("document_type", "").lower()
    if gemini_type in ["certificate", "resume", "cover_letter", "other"]:
        return gemini_type
    
    return "other"


def _transform_to_unified_format(extracted: dict) -> dict:
    """Transform extracted data to unified format with all required fields."""
    return {
        "document_type": extracted.get("document_type", "other"),
        "skills": extracted.get("skills", []) or extracted.get("skills_extracted", []),
        "education": extracted.get("education", []),
        "experience": extracted.get("experience", []),
        "certifications": extracted.get("certifications", []) or extracted.get("certificates", []),
        "projects": extracted.get("projects", []),
        "achievements": extracted.get("achievements", []),
        "summary": extracted.get("summary", "")
    }


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_documents(
    request: Request,
    user_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    Upload multiple career documents and extract data via Gemini multimodal API.
    Accepts PDF, JPG, JPEG, PNG files. Max 5MB each, max 10 files.
    """
    try:
        # --- Validate file count ---
        if len(files) > MAX_FILES:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_FILES} files allowed at once."
            )

        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files provided."
            )

        # --- Read and validate each file ---
        file_parts = []       # Gemini content parts
        file_names = []       # Track processed filenames
        file_contents = []    # Raw bytes for Supabase upload
        storage_urls = []     # URLs of uploaded files

        for f in files:
            if f.content_type not in ALLOWED_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {f.content_type}. Allowed: PDF, JPG, JPEG, PNG."
                )

            content = await f.read()

            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{f.filename}' exceeds 10MB limit."
                )
            
            # Validate actual file content using magic bytes
            validate_file_content(content, f.filename, f.content_type)

            file_names.append(f.filename)
            file_contents.append((f.filename, content, f.content_type))

            # Build Gemini multimodal part
            if f.content_type == "application/pdf":
                # Extract text from PDF and send as text part
                try:
                    text = ""
                    with fitz.open(stream=content, filetype="pdf") as doc:
                        for page in doc:
                            text += page.get_text()
                    if text.strip():
                        file_parts.append(
                            f"\n--- Document: {f.filename} (PDF) ---\n{text.strip()}\n"
                        )
                    else:
                        # If no text (scanned PDF), send as image of each page
                        with fitz.open(stream=content, filetype="pdf") as doc:
                            for page_num, page in enumerate(doc):
                                pix = page.get_pixmap(dpi=150)
                                img_bytes = pix.tobytes("png")
                                file_parts.append(
                                    genai.types.Part.from_bytes(
                                        data=img_bytes,
                                        mime_type="image/png",
                                    )
                                )
                except Exception as pdf_err:
                    print(f"PDF extraction error for {f.filename}: {pdf_err}")
                    # Fallback: skip this file but continue
                    file_parts.append(
                        f"\n--- Document: {f.filename} (PDF - could not extract) ---\n"
                    )
            else:
                # Image file — send directly as multimodal part
                file_parts.append(
                    genai.types.Part.from_bytes(
                        data=content,
                        mime_type=f.content_type,
                    )
                )

        if not file_parts:
            raise HTTPException(
                status_code=400,
                detail="No valid content could be extracted from the uploaded files."
            )

        # --- Upload files to Supabase Storage ---
        storage_urls = []
        for fname, fbytes, ftype in file_contents:
            storage_path = f"{user_id}/documents/{fname}"
            try:
                supabase.storage.from_("user_documents").upload(
                    path=storage_path,
                    file=fbytes,
                    file_options={"content-type": ftype, "upsert": "true"},
                )
                # Get public URL
                public_url = supabase.storage.from_("user_documents").get_public_url(storage_path)
                storage_urls.append({"filename": fname, "url": public_url})
            except Exception as storage_err:
                # Raise a clear error if storage upload fails
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload file '{fname}' to storage. Please try again later."
                )

        # --- Send to Gemini multimodal API with safe wrapper ---
        contents = [EXTRACTION_PROMPT] + file_parts
        extracted = _get_default_extracted_data()
        
        try:
            response = client_genai.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
            )
            raw_text = response.text
            
            # --- Parse extracted JSON ---
            try:
                clean_text = _clean_json(raw_text)
                parsed = json.loads(clean_text)
                # Transform to unified format
                extracted = _transform_to_unified_format(parsed)
            except (json.JSONDecodeError, Exception) as parse_err:
                print(f"JSON parsing warning: {parse_err}")
                # Continue with default structure - don't break upload
                extracted = _get_default_extracted_data()
        
        except Exception as e:
            print(f"[ERROR] Gemini extraction failed for {file_names}: {str(e)}")
            # Return fallback response with 200 status instead of raising 500
            extracted = _get_default_extracted_data()
            extracted["summary"] = "AI service temporarily unavailable"
            extracted["status"] = "failed"
            # Store fallback response in DB
            try:
                for idx, fname in enumerate(file_names):
                    file_doc_type = _detect_document_type(fname, extracted)
                    
                    file_url = None
                    for url_entry in storage_urls:
                        if url_entry.get("filename") == fname:
                            file_url = url_entry.get("url")
                            break
                    
                    doc_record = {
                        "user_id": user_id,
                        "document_name": fname,
                        "document_type": file_doc_type,
                        "extracted_data": extracted,
                        "storage_url": file_url
                    }
                    
                    supabase.table("user_documents").insert(doc_record).execute()
            except Exception as db_err:
                print(f"Fallback storage warning: {db_err}")
            
            return {
                "success": True,
                "fallback": True,
                "extracted": extracted,
                "files_processed": len(file_names),
                "filenames": file_names,
                "file_urls": storage_urls,
                "message": "AI service temporarily unavailable. Documents saved and will be processed soon."
            }

        # --- Detect document type ---
        # Use the first filename as primary for type detection
        primary_filename = file_names[0] if file_names else "document"
        document_type = _detect_document_type(primary_filename, extracted)
        extracted["document_type"] = document_type

        # --- Store each document in user_documents table ---
        # Store one record per file with the extracted data
        try:
            for idx, fname in enumerate(file_names):
                # For multiple files, use the same extraction but detect type per file
                file_doc_type = _detect_document_type(fname, extracted)
                
                # Get storage URL for this file
                file_url = None
                for url_entry in storage_urls:
                    if url_entry.get("filename") == fname:
                        file_url = url_entry.get("url")
                        break
                
                doc_record = {
                    "user_id": user_id,
                    "document_name": fname,
                    "document_type": file_doc_type,
                    "extracted_data": extracted,  # Store the unified JSON structure
                    "storage_url": file_url
                }
                
                supabase.table("user_documents").insert(doc_record).execute()
                print(f"Stored document: {fname} as {file_doc_type}")
        except Exception as db_err:
            print(f"user_documents insert warning: {db_err}")
            # Don't fail - still return the extraction results

        # --- Legacy: Update profiles table with merged data ---
        # Keep this for backward compatibility

        # --- Legacy: Save to Supabase profiles table (backward compatibility) ---
        try:
            # Fetch existing profile data
            profile_resp = supabase.table("profiles").select(
                "extra_skills, certificates"
            ).eq("user_id", user_id).execute()

            existing_skills = []
            existing_certs = []
            if profile_resp.data:
                existing_skills = profile_resp.data[0].get("extra_skills") or []
                existing_certs = profile_resp.data[0].get("certificates") or []

            # Merge new skills (deduplicate)
            new_skills = extracted.get("skills", []) or extracted.get("skills_extracted", [])
            merged_skills = list(set(
                (existing_skills if isinstance(existing_skills, list) else [])
                + (new_skills if isinstance(new_skills, list) else [])
            ))

            # Merge new certificates
            new_certs = extracted.get("certifications", []) or extracted.get("certificates", [])
            merged_certs = (
                (existing_certs if isinstance(existing_certs, list) else [])
                + (new_certs if isinstance(new_certs, list) else [])
            )

            profile_update = {
                "extra_skills": merged_skills,
                "certificates": merged_certs,
                "documents_data": extracted,
            }

            supabase.table("profiles").update(
                profile_update
            ).eq("user_id", user_id).execute()

        except Exception as db_err:
            print(f"Profile update warning: {db_err}")
            # Don't fail — still return the extraction results

        return {
            "success": True,
            "extracted": extracted,
            "files_processed": len(file_names),
            "filenames": file_names,
            "file_urls": storage_urls
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
