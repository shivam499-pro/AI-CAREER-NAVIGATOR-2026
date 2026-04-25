"""
Document Service
Business logic for document operations including:
- Handle resume upload
- Extract skills (basic or AI-ready)
- List documents
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from core.supabase_client import get_supabase


# Common tech skills for basic extraction
TECH_SKILLS = {
    "python", "javascript", "java", "typescript", "go", "golang", "rust", "c++",
    "c#", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    "react", "reactjs", "angular", "vue", "vuejs", "nextjs", "next.js",
    "html", "css", "sass", "less", "tailwind", "bootstrap", "redux",
    "nodejs", "node.js", "express", "fastapi", "flask", "django", "spring",
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "machine learning", "ml", "deep learning", "tensorflow", "pytorch",
    "pandas", "numpy", "scikit-learn", "git", "linux"
}


def extract_basic_skills(text: str) -> List[str]:
    """
    Extract basic skills from text using keyword matching.
    
    Args:
        text: Text to extract skills from
        
    Returns:
        List of skills found
    """
    if not text:
        return []
    
    text_lower = text.lower()
    found_skills = set()
    
    for skill in TECH_SKILLS:
        if skill in text_lower:
            found_skills.add(skill)
    
    return list(found_skills)


def save_document(
    user_id: str,
    document_name: str,
    document_type: str,
    storage_url: Optional[str] = None,
    extracted_data: Optional[Dict[str, Any]] = None
) -> Optional[int]:
    """
    Save a document record.
    
    Args:
        user_id: The user's unique identifier
        document_name: Name of the document
        document_type: Type (certificate/resume/cover_letter/other)
        storage_url: URL to stored file
        extracted_data: Extracted data from document
        
    Returns:
        Document ID if successful
    """
    try:
        supabase = get_supabase()
        
        doc_data = {
            "user_id": user_id,
            "document_name": document_name,
            "document_type": document_type,
            "created_at": datetime.utcnow().isoformat()
        }
        
        if storage_url:
            doc_data["storage_url"] = storage_url
        
        if extracted_data:
            doc_data["extracted_data"] = extracted_data
        else:
            doc_data["extracted_data"] = {}
        
        response = supabase.table("user_documents").insert(doc_data).execute()
        
        if response.data:
            return response.data[0].get("id")
        return None
    except Exception as e:
        print(f"Error saving document: {e}")
        return None


def get_user_documents(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all documents for a user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        List of documents
    """
    try:
        supabase = get_supabase()
        response = supabase.table("user_documents").select(
            "id, document_name, document_type, extracted_data, storage_url, created_at"
        ).eq("user_id", user_id).order("created_at", desc=True).execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching documents: {e}")
        return []


def get_documents_by_type(user_id: str, document_type: str) -> List[Dict[str, Any]]:
    """
    Get documents of a specific type for a user.
    
    Args:
        user_id: The user's unique identifier
        document_type: Type to filter by
        
    Returns:
        List of documents
    """
    try:
        supabase = get_supabase()
        response = supabase.table("user_documents").select(
            "id, document_name, document_type, extracted_data, storage_url, created_at"
        ).eq("user_id", user_id).eq("document_type", document_type).execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching documents: {e}")
        return []


def get_document_by_id(document_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific document by ID.
    
    Args:
        document_id: Document ID
        
    Returns:
        Document data or None
    """
    try:
        supabase = get_supabase()
        response = supabase.table("user_documents").select("*").eq("id", document_id).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching document: {e}")
        return None


def delete_document(document_id: int, user_id: str) -> bool:
    """
    Delete a document (only if owned by user).
    
    Args:
        document_id: Document ID
        user_id: User ID (for authorization)
        
    Returns:
        True if successful
    """
    try:
        supabase = get_supabase()
        response = supabase.table("user_documents").delete().eq("id", document_id).eq("user_id", user_id).execute()
        
        return True
    except Exception as e:
        print(f"Error deleting document: {e}")
        return False


def extract_skills_from_resume(resume_text: str) -> Dict[str, Any]:
    """
    Extract structured data from resume text.
    
    Args:
        resume_text: Resume content
        
    Returns:
        Extracted data
    """
    if not resume_text:
        return {"skills": [], "experience": [], "education": []}
    
    skills = extract_basic_skills(resume_text)
    
    # Basic extraction - in production, use AI for better extraction
    return {
        "skills": skills,
        "experience": [],
        "education": []
    }