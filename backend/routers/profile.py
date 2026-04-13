"""
Profile Router
Exposes the unified profile API for the frontend.
Integrates with profile_builder service to provide merged user skills.
"""
from fastapi import APIRouter, HTTPException
from services.profile_builder import build_user_profile, get_user_documents, get_documents_by_type

router = APIRouter()


@router.get("/profile/{user_id}")
def get_profile(user_id: str):
    """
    Get unified user profile built from all documents.
    
    Returns merged skills with confidence scores from all documents.
    """
    try:
        profile = build_user_profile(user_id)
        return {
            "success": True,
            "profile": profile
        }
    except Exception as e:
        return {
            "success": False,
            "profile": {"skills": []},
            "error": str(e)
        }


@router.get("/profile/{user_id}/documents")
def get_profile_documents(user_id: str):
    """
    Get all documents for a user.
    
    Returns all document records from user_documents table.
    """
    try:
        documents = get_user_documents(user_id)
        return {
            "success": True,
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        return {
            "success": False,
            "documents": [],
            "error": str(e)
        }


@router.get("/profile/{user_id}/documents/{document_type}")
def get_profile_documents_by_type(user_id: str, document_type: str):
    """
    Get documents of a specific type for a user.
    
    Args:
        user_id: The user's unique identifier
        document_type: Filter by type (certificate/resume/cover_letter/other)
    """
    try:
        documents = get_documents_by_type(user_id, document_type)
        return {
            "success": True,
            "document_type": document_type,
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        return {
            "success": False,
            "documents": [],
            "error": str(e)
        }