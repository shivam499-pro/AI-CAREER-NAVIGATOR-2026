"""
Documents Router
Unified documents API endpoints.

POST /api/documents/upload - Upload document
GET /api/documents/list - List documents
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, List
from pydantic import BaseModel
from services import document_service
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()


# Request Models
class DocumentUploadRequest(BaseModel):
    """Document upload request."""
    document_name: str
    document_type: str  # certificate, resume, cover_letter, other
    storage_url: Optional[str] = None
    content: Optional[str] = None  # For text content


async def get_user_from_token(authorization: Optional[str] = Header(None)) -> str:
    """Extract user_id from authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    token = authorization.replace("Bearer ", "")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            user_resp = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {token}"
                }
            )
            if user_resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            user_info = user_resp.json()
            user_id = user_info.get("id")
            
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            return user_id
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/upload")
async def upload_document(
    document: DocumentUploadRequest,
    user_id: str = Depends(get_user_from_token)
):
    """
    Upload a document.
    
    Saves document record with extracted skills.
    """
    try:
        # Extract skills if content provided
        extracted_data = {}
        if document.content:
            extracted_data = document_service.extract_skills_from_resume(document.content)
        
        # Save document
        doc_id = document_service.save_document(
            user_id=user_id,
            document_name=document.document_name,
            document_type=document.document_type,
            storage_url=document.storage_url,
            extracted_data=extracted_data
        )
        
        if doc_id:
            return {
                "success": True,
                "document_id": doc_id,
                "message": "Document uploaded successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upload document")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_documents(
    document_type: Optional[str] = None,
    user_id: str = Depends(get_user_from_token)
):
    """
    List all documents for current user.
    
    Optionally filter by document type.
    """
    try:
        if document_type:
            documents = document_service.get_documents_by_type(user_id, document_type)
        else:
            documents = document_service.get_user_documents(user_id)
        
        return {
            "success": True,
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    user_id: str = Depends(get_user_from_token)
):
    """
    Get a specific document.
    """
    try:
        document = document_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify ownership
        if document.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "success": True,
            "document": document
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    user_id: str = Depends(get_user_from_token)
):
    """
    Delete a document.
    """
    try:
        success = document_service.delete_document(document_id, user_id)
        
        if success:
            return {
                "success": True,
                "message": "Document deleted successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
