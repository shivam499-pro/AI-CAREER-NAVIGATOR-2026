import asyncio
import os
import uuid
from core.supabase_client import get_supabase
from dotenv import load_dotenv
from modules.interview.repository import InterviewRepository

load_dotenv()

class InterviewModuleService:
    def __init__(self):
        self._active_sessions = {}
        self.repository = InterviewRepository()
    @property
    def supabase(self):
        return get_supabase()

    def get_or_create_session(
        self,
        user_id: str,
        career_path: str,
    ) -> str:
        session_key = f"{user_id}:{career_path}"

        if session_key not in self._active_sessions:
            self._active_sessions[session_key] = str(uuid.uuid4())

        return self._active_sessions[session_key]

    async def save_session_data(
        self,
        session_data: dict,
        interview_rows: list,
    ):
        await self.repository.save_interview_session(
            session_data
        )

        if interview_rows:
            await self.repository.save_interview_rows(
                interview_rows
            )
            
    async def prepare_interview_profile(self, user_id: str) -> dict:
        profile_res, analysis_res = await asyncio.gather(
            self.repository.get_profile_by_user_id(user_id),
            self.repository.get_analysis_by_user_id(user_id),
        )
        if not profile_res.data:
            return {}

        profile = profile_res.data[0]
        analysis_data = analysis_res.data[0] if analysis_res.data else {}

        return {
        "college_name": profile.get("college_name"),
        "degree": profile.get("degree"),
        "branch": profile.get("branch"),
        "extra_skills": profile.get("extra_skills", []),
        "experience": profile.get("experience", []),
        "certificates": profile.get("certificates", []),
        "career_goal": profile.get("career_goal"),
        "resume_text": profile.get("resume_text"),
        "github_username": profile.get("github_username"),
        "strengths": analysis_data.get("analysis", {}).get("strengths", []),
        "career_paths": analysis_data.get("career_paths", []),
    }

    