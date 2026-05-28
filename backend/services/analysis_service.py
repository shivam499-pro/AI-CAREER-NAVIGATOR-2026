"""
Analysis Service - Phase 2 (SRP + OCP Fix)
- No direct DB calls (repository handles that)
- No hardcoded data sources (provider registry handles that)
- Adding a new data source = add a provider, nothing else changes here
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from services.profile_service import get_enriched_profile
from services import gemini_service
from repositories.analysis_repository import AnalysisRepository, SupabaseAnalysisRepository
from services.data_providers import DataProvider, DEFAULT_PROVIDERS


def _get_repository() -> AnalysisRepository:
    return SupabaseAnalysisRepository()


def get_analysis_by_user_id(
    user_id: str,
    repository: AnalysisRepository = None
) -> Optional[Dict[str, Any]]:
    """Get analysis for a user."""
    repo = repository or _get_repository()
    return repo.get_by_user_id(user_id)


def save_analysis(
    user_id: str,
    analysis_data: Dict[str, Any],
    repository: AnalysisRepository = None
) -> bool:
    """Save analysis results."""
    repo = repository or _get_repository()

    data = {
        "user_id": user_id,
        "updated_at": datetime.utcnow().isoformat()
    }

    analysis_obj = {}
    if "strengths" in analysis_data:
        analysis_obj["strengths"] = analysis_data["strengths"]
        data["strengths"] = analysis_data["strengths"]
    if "weaknesses" in analysis_data:
        analysis_obj["weaknesses"] = analysis_data["weaknesses"]
        data["weaknesses"] = analysis_data["weaknesses"]
    if "experience_level" in analysis_data:
        analysis_obj["experience_level"] = analysis_data["experience_level"]
        data["experience_level"] = analysis_data["experience_level"]
    if "career_paths" in analysis_data:
        data["career_paths"] = analysis_data["career_paths"]
    if "skill_gaps" in analysis_data:
        analysis_obj["skill_gaps"] = analysis_data["skill_gaps"]
        data["skill_gaps"] = analysis_data["skill_gaps"]

    if analysis_obj:
        data["analysis"] = analysis_obj

    return repo.upsert(data)


async def run_analysis(
    user_id: str,
    repository: AnalysisRepository = None,
    providers: List[DataProvider] = None
) -> Dict[str, Any]:
    """
    Run AI analysis for a user.
    
    providers: injectable list of DataProvider instances.
               Defaults to DEFAULT_PROVIDERS (GitHub + LeetCode).
               Pass custom providers in tests or to add new sources.
    """
    repo = repository or _get_repository()
    active_providers = providers or DEFAULT_PROVIDERS

    try:
        profile = get_enriched_profile(user_id)

        if not profile.get("exists"):
            return {
                "success": False,
                "error": "Profile not found. Please complete your profile first."
            }

        profile_data = profile.get("data", {})
        print("PROFILE DATA:", profile_data)

        # ── Fetch data from all registered providers ──────────────────────
        # To add HackerRank: add HackerrankDataProvider to DEFAULT_PROVIDERS.
        # This loop never changes.
        source_data: Dict[str, Any] = {}
        for provider in active_providers:
            username = profile_data.get(f"{provider.source_name}_username", "")
            if username:
                print(f"{provider.source_name.upper()} USERNAME:", username)
                source_data[provider.source_name] = await provider.fetch_data(username)
                print(f"{provider.source_name.upper()} DATA:", source_data[provider.source_name])
            else:
                source_data[provider.source_name] = {}

        github_data = source_data.get("github", {})
        leetcode_data = source_data.get("leetcode", {})

        resume_text = profile_data.get("resume_text", "")

        result = gemini_service.run_combined_analysis(
            github_data,
            leetcode_data,
            resume_text,
            profile_data
        )
        print("GEMINI RESULT:", result)

        if result.get("success") == False:
            error_msg = result.get("error", "Unknown error from Gemini")
            raise Exception(error_msg)

        analysis_result = result.get("data", {})

        save_data = {
            "user_id": user_id,
            "github_data": github_data,
            "leetcode_data": leetcode_data,
            "analysis": analysis_result,
            "career_paths": analysis_result.get("career_paths", []),
            "skill_gaps": analysis_result.get("skill_gaps", []),
            "roadmap": analysis_result.get("roadmap", {}),
            "path_details": analysis_result.get("path_details", {}),
            "experience_level": analysis_result.get("analysis", {}).get("experience_level", "Intermediate"),
            "resume_score": analysis_result.get("resume_score", {}),
            "salary_insights": analysis_result.get("salary_insights", {}),
            "top_companies": analysis_result.get("top_companies", []),
            "certifications": analysis_result.get("certifications", []),
            "updated_at": datetime.utcnow().isoformat()
        }

        repo.upsert(save_data)

        return {
            "success": True,
            "analysis": analysis_result
        }

    except Exception as e:
        print(f"Error running analysis: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_career_recommendations(
    user_id: str,
    limit: int = 5,
    repository: AnalysisRepository = None
) -> List[Dict[str, Any]]:
    """Get career path recommendations."""
    try:
        analysis = get_analysis_by_user_id(user_id, repository)
        if not analysis or not analysis.get("career_paths"):
            return []
        return analysis.get("career_paths", [])[:limit]
    except Exception as e:
        print(f"Error getting career recommendations: {e}")
        return []


def get_skill_gaps(
    user_id: str,
    repository: AnalysisRepository = None
) -> List[Dict[str, Any]]:
    """Get skill gaps for a user."""
    try:
        analysis = get_analysis_by_user_id(user_id, repository)
        if not analysis:
            return []
        return analysis.get("skill_gaps", [])
    except Exception as e:
        print(f"Error getting skill gaps: {e}")
        return []