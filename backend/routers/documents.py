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
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per file
MAX_FILES = 10

EXTRACTION_PROMPT = """You are analyzing career documents for a student/professional.
Extract ALL relevant information from these documents including:
1. Certificate names and issuing organizations
2. Dates earned/issued
3. Skills and technologies mentioned
4. Grades, scores, or percentages
5. Course names and durations
6. Any achievements or awards

Return ONLY a valid JSON object:
{
  "certificates": [
    {
      "name": "certificate name",
      "issuer": "organization name",
      "date": "date earned",
      "skills": ["skill1", "skill2"]
    }
  ],
  "skills_extracted": ["skill1", "skill2"],
  "grades": [
    {
      "subject": "subject name",
      "score": "score/grade"
    }
  ],
  "achievements": ["achievement1", "achievement2"],
  "summary": "brief summary of all documents"
}"""


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
                    detail=f"File '{f.filename}' exceeds 5MB limit."
                )

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

        # --- Send to Gemini multimodal API ---
        contents = [EXTRACTION_PROMPT] + file_parts
        try:
            response = client_genai.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
            )
            raw_text = response.text
        except Exception as gemini_err:
            raise HTTPException(
                status_code=500,
                detail=f"AI analysis failed: {str(gemini_err)}"
            )

        # --- Parse extracted JSON ---
        try:
            clean_text = _clean_json(raw_text)
            extracted = json.loads(clean_text)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="AI returned an invalid response. Please try again."
            )

        # --- Ensure expected keys ---
        extracted.setdefault("certificates", [])
        extracted.setdefault("skills_extracted", [])
        extracted.setdefault("grades", [])
        extracted.setdefault("achievements", [])
        extracted.setdefault("summary", "")

        # --- Save to Supabase profiles table ---
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
            new_skills = extracted.get("skills_extracted", [])
            merged_skills = list(set(
                (existing_skills if isinstance(existing_skills, list) else [])
                + (new_skills if isinstance(new_skills, list) else [])
            ))

            # Merge new certificates
            new_certs = extracted.get("certificates", [])
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
