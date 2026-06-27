import asyncio
from core.supabase_client import get_supabase


class InterviewRepository:
    async def get_profile_by_user_id(self, user_id: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: get_supabase().table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

    async def get_analysis_by_user_id(self, user_id: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: get_supabase().table("analyses")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

    async def save_interview_session(
        self,
        session_data: dict,
    ):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: get_supabase().table("interview_sessions")
            .insert(session_data)
            .execute()
        )

    async def save_interview_rows(
        self,
        interview_rows: list,
    ):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: get_supabase().table("interviews")
            .insert(interview_rows)
            .execute()
        )