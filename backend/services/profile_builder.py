"""
Profile Builder Service
Merges all documents from user_documents table into a unified user profile.
This is the core intelligence layer that creates a consolidated view of user skills.
"""
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Document type confidence weights
# Higher weight = more reliable source
DOCUMENT_WEIGHTS = {
    "certificate": 0.9,    # Official certificates are very reliable
    "resume": 0.6,       # Resume is self-reported but verified context
    "cover_letter": 0.5, # Cover letter shows intent
    "other": 0.4         # Generic documents
}
DEFAULT_WEIGHT = 0.5  # Default for unknown source types


def build_user_profile(user_id: str) -> dict:
    """
    Build a unified user profile by merging all documents from user_documents table.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        dict with merged skills from all documents
        {
            "skills": [
                {
                    "name": "Python",
                    "count": 2,
                    "sources": ["resume", "certificate"]
                },
                ...
            ]
        }
    """
    try:
        # Fetch all documents for the user
        response = supabase.table("user_documents").select(
            "document_name, document_type, extracted_data"
        ).eq("user_id", user_id).execute()
        
        if not response.data:
            return {"skills": []}
        
        skills_map = {}
        
        # Loop through each document
        for doc in response.data:
            data = doc.get("extracted_data", {})
            doc_type = doc.get("document_type", "other")
            
            # Process skills from this document
            for skill in data.get("skills", []):
                skill_lower = skill.lower().strip()
                
                if not skill_lower:
                    continue
                
                if skill_lower not in skills_map:
                    skills_map[skill_lower] = {
                        "name": skill.strip(),  # Keep original case
                        "sources": [],
                        "count": 0
                    }
                
                # Increment count and add source if not already added
                skills_map[skill_lower]["count"] += 1
                if doc_type not in skills_map[skill_lower]["sources"]:
                    skills_map[skill_lower]["sources"].append(doc_type)
        
        # Calculate confidence score for each skill
        for skill_key in skills_map:
            sources = skills_map[skill_key]["sources"]
            if sources:
                # Compute average confidence from all sources
                total_weight = sum(DOCUMENT_WEIGHTS.get(s, DEFAULT_WEIGHT) for s in sources)
                avg_confidence = total_weight / len(sources)
                # Round to 2 decimal places
                skills_map[skill_key]["confidence"] = round(avg_confidence, 2)
            else:
                skills_map[skill_key]["confidence"] = 0.0
        
        # Convert to sorted list (by confidence descending, then count)
        skills_list = list(skills_map.values())
        skills_list.sort(key=lambda x: (-x["confidence"], -x["count"]), reverse=True)
        
        return {
            "skills": skills_list
        }
        
    except Exception as e:
        print(f"Profile build error: {e}")
        return {"skills": []}


def get_user_documents(user_id: str) -> list:
    """
    Fetch all documents for a user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        List of document records
    """
    try:
        response = supabase.table("user_documents").select(
            "id, document_name, document_type, extracted_data, storage_url, created_at"
        ).eq("user_id", user_id).execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        print(f"Get user documents error: {e}")
        return []


def get_documents_by_type(user_id: str, document_type: str) -> list:
    """
    Fetch documents of a specific type for a user.
    
    Args:
        user_id: The user's unique identifier
        document_type: The type of document to fetch (certificate/resume/cover_letter/other)
        
    Returns:
        List of document records of the specified type
    """
    try:
        response = supabase.table("user_documents").select(
            "id, document_name, document_type, extracted_data, storage_url, created_at"
        ).eq("user_id", user_id).eq("document_type", document_type).execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        print(f"Get documents by type error: {e}")
        return []