from services.interview_service import (
    InterviewService,
    InterviewServiceConfig,
)

from core.gemini_transport import AsyncGeminiTransport

import uuid


_interview_service = None

_user_active_sessions = {}


def get_interview_service() -> InterviewService:
    global _interview_service

    if _interview_service is None:
        _interview_service = InterviewService(
            transport=AsyncGeminiTransport.create(),
            config=InterviewServiceConfig(
                questions_cache_ttl_seconds=900,
                user_throttle_seconds=20,
                max_cached_question_sets=100,
            ),
        )

    return _interview_service


def get_or_create_session(
    user_id: str,
    career_path: str,
) -> str:

    session_key = f"{user_id}:{career_path}"

    if session_key not in _user_active_sessions:
        _user_active_sessions[session_key] = str(uuid.uuid4())

    return _user_active_sessions[session_key]