"""
Documents Router
Unified documents API endpoints.

POST /api/v1/documents/upload-files         - Upload + AI analyze certificates
GET  /api/v1/documents/list                 - List documents
GET  /api/v1/documents/{document_id}        - Get single document
DELETE /api/v1/documents/{document_id}      - Delete document
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from typing import Optional, List
from pydantic import BaseModel
from services import document_service
from core.middleware import get_current_user, AuthenticatedUser
from supabase import create_client
from services.certificate_service import CertificateService    # ← ADD THIS
from core.gemini_transport import AsyncGeminiTransport
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

router  = APIRouter()

# Certificate service — initialized once, transport injected (DIP)
_certificate_service = None

def _get_certificate_service():
    global _certificate_service
    if _certificate_service is None:
        _certificate_service = CertificateService(
            transport=AsyncGeminiTransport.create()
        )
    return _certificate_service

# ─── Supabase ─────────────────────────────────────────────────────────────────

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)

# ─── Allowed file types for certificates ──────────────────────────────────────

ALLOWED_CERT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg":      ".jpg",
    "image/jpg":       ".jpg",
    "image/png":       ".png",
}


MAX_CERT_SIZE = 5 * 1024 * 1024
MAX_FILE_SIZE = MAX_CERT_SIZE
ALLOWED_TYPES = ALLOWED_CERT_TYPES
MAX_CERT_FILES = 10
PDF_MAGIC_BYTES  = b"%PDF"
JPEG_MAGIC_BYTES = b"\xff\xd8"
PNG_MAGIC_BYTES  = b"\x89PNG\r\n\x1a\n"


def validate_file_content(
    content: bytes,
    filename: str,
    mime_type: str,
    min_image_size: int = 10
) -> None:
    """
    Validate file content using magic bytes.
    Raises HTTPException(400) on invalid content.
    """
    from fastapi import HTTPException
    
    if mime_type == "application/pdf":
        if not content.startswith(PDF_MAGIC_BYTES):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF: file does not start with %PDF signature"
            )
    elif mime_type in ("image/jpeg", "image/jpg"):
        if not content.startswith(JPEG_MAGIC_BYTES):
            raise HTTPException(
                status_code=400,
                detail="Invalid JPEG: incorrect file signature"
            )
        if len(content) < min_image_size:
            raise HTTPException(
                status_code=400,
                detail="Invalid image: file too small to be a valid JPEG"
            )
    elif mime_type == "image/png":
        if not content.startswith(PNG_MAGIC_BYTES):
            raise HTTPException(
                status_code=400,
                detail="Invalid PNG: incorrect file signature"
            )            
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {mime_type}"
        )

# ─── POST /upload-certificates ────────────────────────────────────────────────

@router.post("/upload-files")
async def upload_certificates(
    request:      Request,
    files:        List[UploadFile] = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Upload and AI-analyze certificate files.
    
    Accepts: PDF, JPG, PNG (max 5MB each, max 10 files)
    
    For each file Gemini extracts:
    - Course name, provider, score, date
    - Skills unlocked
    - Certificate weight (1-10)
    - Credibility (high/medium/low)
    
    Saves to user_documents + updates profiles.extra_skills
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    if len(files) > MAX_CERT_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_CERT_FILES} files allowed per upload."
        )

    user_id   = current_user.user_id
    sb        = get_supabase()
    results   = []
    all_skills: set = set()

    for file in files:
        # ── Validate ──────────────────────────────────────────────────────────
        if file.content_type not in ALLOWED_CERT_TYPES:
            results.append({
                "filename": file.filename,
                "success":  False,
                "error":    f"Unsupported type: {file.content_type}"
            })
            continue

        content = await file.read()

        if len(content) > MAX_CERT_SIZE:
            results.append({
                "filename": file.filename,
                "success":  False,
                "error":    "File exceeds 5MB limit."
            })
            continue

        # ── AI analysis ───────────────────────────────────────────────────────
        try:
            cert_result = await _get_certificate_service().analyze(
                file_content=content,
                filename=file.filename or "certificate",
                mime_type=file.content_type
            )
            extracted = cert_result.data
        except Exception as ai_err:
            print(f"[Cert AI] Failed for {file.filename}: {ai_err}")
            extracted = {
                "course_name":        file.filename,
                "provider":           "Unknown",
                "skills_unlocked":    [],
                "certificate_weight": 5,
                "credibility":        "medium",
                "summary":            "AI analysis unavailable.",
                "document_type":      "certificate"
            }

        # ── Save to user_documents ────────────────────────────────────────────
        try:
            doc_record = {
                "user_id":       user_id,
                "document_name": file.filename,
                "document_type": "certificate",
                "extracted_data": extracted,
                "storage_url":   None,
                "created_at":    datetime.now(timezone.utc).isoformat()
            }
            sb.table("user_documents").insert(doc_record).execute()
        except Exception as db_err:
            print(f"[Cert DB] Insert failed for {file.filename}: {db_err}")
            results.append({
                "filename": file.filename,
                "success":  False,
                "error":    "Database save failed."
            })
            continue

        # Collect skills for profile update
        all_skills.update(extracted.get("skills_unlocked", []))

        results.append({
            "filename":   file.filename,
            "success":    True,
            "extracted":  extracted
        })

    # ── Update profiles.extra_skills with newly unlocked skills ───────────────
    if all_skills:
        try:
            # Get current extra_skills
            profile_res = sb.table("profiles") \
                .select("extra_skills") \
                .eq("user_id", user_id) \
                .execute()

            current_skills: list = []
            if profile_res.data:
                current_skills = profile_res.data[0].get("extra_skills") or []

            # Merge without duplicates (case-insensitive)
            existing_lower = {s.lower() for s in current_skills}
            new_skills     = [s for s in all_skills if s.lower() not in existing_lower]
            merged         = current_skills + new_skills

            sb.table("profiles") \
                .update({"extra_skills": merged}) \
                .eq("user_id", user_id) \
                .execute()

        except Exception as profile_err:
            print(f"[Cert] Profile skills update failed: {profile_err}")
            # Non-critical — don't fail the response

    # ── Summary ───────────────────────────────────────────────────────────────
    successful   = [r for r in results if r.get("success")]
    failed       = [r for r in results if not r.get("success")]
    skills_added = list(all_skills)

    return {
        "success":        len(successful) > 0,
        "files_processed": len(successful),
        "files_failed":    len(failed),
        "skills_added":    skills_added,
        "results":         results,
        "message":        f"{len(successful)} certificate(s) analyzed successfully."
    }


# ─── GET /list ────────────────────────────────────────────────────────────────

@router.get("/list")
async def list_documents(
    document_type: Optional[str] = None,
    current_user:  AuthenticatedUser = Depends(get_current_user)
):
    """List all documents for current user, optionally filtered by type."""
    try:
        if document_type:
            documents = document_service.get_documents_by_type(
                current_user.user_id, document_type
            )
        else:
            documents = document_service.get_user_documents(current_user.user_id)

        return {
            "success":   True,
            "documents": documents,
            "count":     len(documents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── GET /{document_id} ───────────────────────────────────────────────────────

@router.get("/{document_id}")
async def get_document(
    document_id:  str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get a specific document by ID."""
    try:
        document = document_service.get_document_by_id(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")

        if document.get("user_id") != current_user.user_id:
            raise HTTPException(status_code=403, detail="Access denied.")

        return {"success": True, "document": document}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── DELETE /{document_id} ───────────────────────────────────────────────────

@router.delete("/{document_id}")
async def delete_document(
    document_id:  str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a document (only if owned by current user)."""
    try:
        success = document_service.delete_document(document_id, current_user.user_id)

        if success:
            return {"success": True, "message": "Document deleted."}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))