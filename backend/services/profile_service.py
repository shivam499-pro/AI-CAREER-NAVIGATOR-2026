"""
Profile Service
Business logic for profile operations including:
- Merging resume skills + manual skills
- Calculating completeness score
- Preparing enriched profile
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from core.supabase_client import get_supabase


# Document type confidence weights
DOCUMENT_WEIGHTS = {
    "certificate": 0.9,
    "resume": 0.6,
    "cover_letter": 0.5,
    "other": 0.4
}
DEFAULT_WEIGHT = 0.5


def get_profile_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get profile by user ID.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        Profile data or None
    """
    try:
        supabase = get_supabase()
        response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return None


def save_profile(user_id: str, profile_data: Dict[str, Any]) -> bool:
    """
    Save or update user profile.
    
    Args:
        user_id: The user's unique identifier
        profile_data: Profile data to save
        
    Returns:
        True if successful
    """
    try:
        supabase = get_supabase()
        
        # Add updated timestamp
        profile_data["user_id"] = user_id
        profile_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("profiles").upsert(profile_data).execute()
        
        return bool(response.data)
    except Exception as e:
        print(f"Error saving profile: {e}")
        return False


def merge_skills_from_documents(user_id: str) -> List[Dict[str, Any]]:
    """
    Merge skills from all user documents (resume, certificates, etc.)
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        List of merged skills with confidence scores
    """
    try:
        supabase = get_supabase()
        response = supabase.table("user_documents").select(
            "document_name, document_type, extracted_data"
        ).eq("user_id", user_id).execute()
        
        if not response.data:
            return []
        
        skills_map = {}
        
        for doc in response.data:
            data = doc.get("extracted_data", {})
            doc_type = doc.get("document_type", "other")
            
            for skill in data.get("skills", []):
                skill_lower = skill.lower().strip()
                
                if not skill_lower:
                    continue
                
                if skill_lower not in skills_map:
                    skills_map[skill_lower] = {
                        "name": skill.strip(),
                        "sources": [],
                        "count": 0
                    }
                
                skills_map[skill_lower]["count"] += 1
                if doc_type not in skills_map[skill_lower]["sources"]:
                    skills_map[skill_lower]["sources"].append(doc_type)
        
        # Calculate confidence scores
        for skill_key in skills_map:
            sources = skills_map[skill_key]["sources"]
            if sources:
                total_weight = sum(DOCUMENT_WEIGHTS.get(s, DEFAULT_WEIGHT) for s in sources)
                avg_confidence = total_weight / len(sources)
                skills_map[skill_key]["confidence"] = round(avg_confidence, 2)
            else:
                skills_map[skill_key]["confidence"] = 0.0
        
        # Convert to sorted list
        skills_list = list(skills_map.values())
        skills_list.sort(key=lambda x: (-x["confidence"], -x["count"]), reverse=True)
        
        return skills_list
    except Exception as e:
        print(f"Error merging skills: {e}")
        return []


def calculate_profile_completeness(profile: Optional[Dict[str, Any]], documents: List[Dict[str, Any]] = None) -> int:
    """
    Calculate profile completeness score (0-100).
    
    Args:
        profile: Profile data
        documents: List of user documents
        
    Returns:
        Completeness score
    """
    score = 0
    
    if not profile:
        return 0
    
    # Basic info (30%)
    if profile.get("college_name"):
        score += 10
    if profile.get("degree"):
        score += 10
    if profile.get("branch"):
        score += 10
    
    # External links (30%)
    if profile.get("github_username"):
        score += 15
    if profile.get("leetcode_username"):
        score += 15
    
    # Skills (20%)
    if profile.get("extra_skills") and len(profile.get("extra_skills", [])) >= 3:
        score += 20
    
    # Documents/Resume (20%)
    has_resume = False
    if documents:
        for doc in documents:
            if doc.get("document_type") == "resume":
                has_resume = True
                break
    if has_resume:
        score += 20
    elif profile.get("resume_text"):
        score += 20
    
    return min(score, 100)


def get_enriched_profile(user_id: str) -> Dict[str, Any]:
    """
    Get enriched profile with merged skills and completeness score.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        Enriched profile data
    """
    # Get base profile
    profile = get_profile_by_user_id(user_id)
    
    if not profile:
        return {
            "exists": False,
            "user_id": user_id,
            "completeness": 0,
            "skills": [],
            "data": {}
        }
    
    # Get documents
    try:
        supabase = get_supabase()
        docs_response = supabase.table("user_documents").select(
            "id, document_name, document_type, extracted_data, storage_url, created_at"
        ).eq("user_id", user_id).execute()
        documents = docs_response.data if docs_response.data else []
    except:
        documents = []
    
    # Merge skills from documents with manual skills
    document_skills = merge_skills_from_documents(user_id)
    manual_skills = profile.get("extra_skills", [])
    
    # Combine skills
    all_skills = []
    skill_names = set()
    
    # Add document skills first (higher confidence)
    for doc_skill in document_skills:
        skill_names.add(doc_skill["name"].lower())
        all_skills.append({
            **doc_skill,
            "source": "document"
        })
    
    # Add manual skills
    for skill in manual_skills:
        if skill.lower() not in skill_names:
            all_skills.append({
                "name": skill,
                "count": 1,
                "sources": ["manual"],
                "confidence": 0.8,
                "source": "manual"
            })
    
    # Calculate completeness
    completeness = calculate_profile_completeness(profile, documents)
    
    return {
        "exists": True,
        "user_id": user_id,
        "completeness": completeness,
        "skills": all_skills,
        "data": profile,
        "documents_count": len(documents)
    }


def get_user_progress(user_id: str) -> Dict[str, Any]:
    """
    Calculate user progress through the career journey.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        Progress data with steps
    """
    try:
        supabase = get_supabase()
        
        # 1. Identity Phase - Profile exists
        profile_res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        profile = profile_res.data[0] if profile_res.data else None
        
        # 2. Sync Phase - External accounts connected
        is_synced = False
        if profile:
            is_synced = bool(profile.get("github_username") or profile.get("leetcode_username"))
        
        # 3. Analysis Phase
        analysis_res = supabase.table("analyses").select("id").eq("user_id", user_id).execute()
        has_analysis = len(analysis_res.data) > 0
        
        # 4. Simulation Phase
        interview_res = supabase.table("interviews").select("id").eq("user_id", user_id).execute()
        has_interview = len(interview_res.data) > 0
        
        steps = [
            {
                "id": "identity",
                "label": "Identity Established",
                "desc": "Account Initialized",
                "status": "complete" if profile else "pending",
                "value": 25 if profile else 0
            },
            {
                "id": "sync",
                "label": "Intelligence Synced",
                "desc": "External Nodes Connected",
                "status": "complete" if is_synced else "pending",
                "value": 25 if is_synced else 0
            },
            {
                "id": "analysis",
                "label": "Analysis Ready",
                "desc": "AI Strategic Analysis Complete",
                "status": "complete" if has_analysis else "pending",
                "value": 25 if has_analysis else 0
            },
            {
                "id": "simulation",
                "label": "Boardroom Simulation",
                "desc": "Live Practice Interview Recorded",
                "status": "complete" if has_interview else "pending",
                "value": 25 if has_interview else 0
            }
        ]
        
        total_progress = sum(s["value"] for s in steps)
        
        return {
            "total": total_progress,
            "steps": steps,
            "status": "ELITE" if total_progress == 100 else "EXECUTIVE" if total_progress >= 50 else "INITIALIZED"
        }
    except Exception as e:
        return {"error": str(e), "total": 0, "steps": []}