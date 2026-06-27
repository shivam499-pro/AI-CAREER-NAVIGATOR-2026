from __future__ import annotations

import asyncio
import logging
import time
import uuid
import json
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from core.gemini_transport import AsyncGeminiTransport

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class InterviewServiceConfig:
    """Configuration for InterviewService."""
    
    # Cache settings
    questions_cache_ttl_seconds: int = 900  # 15 minutes
    max_cached_question_sets: int = 100
    
    # Throttling settings
    user_throttle_seconds: int = 20
    
    # Retry settings
    max_ai_retries: int = 2
    retry_delay_seconds: float = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Fallback question bank
# ─────────────────────────────────────────────────────────────────────────────

FALLBACK_QUESTIONS = [
    {
        "id": 1,
        "question": "Tell me about yourself and why you're interested in this role.",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Focus on your background, key skills, and why this career path interests you."
    },
    {
        "id": 2,
        "question": "Describe a challenging project you worked on. What was the problem and how did you solve it?",
        "type": "project_based",
        "difficulty": "medium",
        "hint": "Use STAR method: Situation, Task, Action, Result. Be specific about your contribution."
    },
    {
        "id": 3,
        "question": "What are your strengths and how do they help you in this role?",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Pick 2-3 relevant strengths with concrete examples from your experience."
    },
    {
        "id": 4,
        "question": "Where do you see yourself in 5 years?",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Align your answer with the career path and show ambition balanced with realism."
    },
    {
        "id": 5,
        "question": "Describe a time when you had to learn something new quickly. How did you approach it?",
        "type": "behavioral",
        "difficulty": "medium",
        "hint": "Show your learning ability and adaptability. Include specific steps you took."
    },
    {
        "id": 6,
        "question": "What are your salary expectations?",
        "type": "behavioral",
        "difficulty": "medium",
        "hint": "Research the market rate for your role and experience level. Give a range."
    },
    {
        "id": 7,
        "question": "Why do you want to work at this company?",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Research the company. Mention specific values, products, or recent achievements."
    },
    {
        "id": 8,
        "question": "Tell me about a time you failed and what you learned from it.",
        "type": "behavioral",
        "difficulty": "medium",
        "hint": "Be honest but focus on what you learned and how you improved afterward."
    },
    {
        "id": 9,
        "question": "What questions do you have for me?",
        "type": "behavioral",
        "difficulty": "easy",
        "hint": "Ask about team culture, immediate priorities, or growth opportunities."
    },
    {
        "id": 10,
        "question": "Describe a technical problem you solved. What was your approach?",
        "type": "technical",
        "difficulty": "medium",
        "hint": "Explain the problem clearly, walk through your solution, and mention the outcome."
    }
]


# ─────────────────────────────────────────────────────────────────────────────
# Core service class
# ─────────────────────────────────────────────────────────────────────────────

class InterviewService:
    """
    Service for interview question generation and answer evaluation.
    
    DIP: Receives AsyncGeminiTransport via constructor.
    """

    def __init__(
        self,
        *,
        transport: AsyncGeminiTransport,
        config: InterviewServiceConfig = None,
    ):
        """
        Args:
            transport: AsyncGeminiTransport instance (injected, no global state)
            config: InterviewServiceConfig (defaults to standard values)
        """
        self._transport = transport
        self._config = config or InterviewServiceConfig()
        
        # In-memory cache: {cache_key: (timestamp, questions_list)}
        self._questions_cache: Dict[str, tuple] = OrderedDict()
        
        # Per-user throttle tracking: {user_id: last_request_timestamp}
        self._user_last_request_time: Dict[str, float] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    async def generate_questions(
        self,
        user_id: str,
        career_path: str,
        difficulty: str = "medium",
        personality: str = "friendly",
        interview_mode: str = "technical",
        profile: Dict[str, Any] = None,
        resume_text: str = "",
    ) -> Dict[str, Any]:
        """Generate interview questions for a user with caching and fallback."""
        session_id = str(uuid.uuid4())
        
        try:
            # Check throttling
            if self._is_user_throttled(user_id):
                cached = self._get_cached_questions(user_id, career_path, difficulty)
                if cached:
                    return {
                        "success": True,
                        "questions": cached,
                        "source": "throttle_cache",
                        "meta": {"cached": True, "retry_used": False, "session_id": session_id}
                    }
                fallback = self._get_fallback_questions()
                return {
                    "success": True,
                    "questions": fallback,
                    "source": "throttle_fallback",
                    "meta": {"cached": False, "retry_used": False, "session_id": session_id}
                }
            
            # Check cache
            cached = self._get_cached_questions(user_id, career_path, difficulty)
            if cached:
                return {
                    "success": True,
                    "questions": cached,
                    "source": "cache",
                    "meta": {"cached": True, "retry_used": False, "session_id": session_id}
                }
            
            # Call AI
            questions = None
            retry_used = False
            
            try:
                questions = await self._call_gemini_for_questions(
                    profile or {},
                    career_path,
                    difficulty,
                    resume_text,
                    personality,
                    interview_mode
                )
            except Exception as ai_error:
                error_str = str(ai_error).lower()
                if "rate limit" in error_str or "429" in error_str:
                    retry_used = True
                    try:
                        await asyncio.sleep(self._config.retry_delay_seconds)
                        questions = await self._call_gemini_for_questions(
                            profile or {},
                            career_path,
                            difficulty,
                            resume_text,
                            personality,
                            interview_mode
                        )
                    except Exception:
                        questions = None
                else:
                    raise
            
            # Check if valid
            if questions and len(questions) > 0:
                unique_questions = self._deduplicate_questions(questions)
                
                if len(unique_questions) < 3:
                    fallback = self._get_fallback_questions()
                    unique_questions.extend(fallback[:5 - len(unique_questions)])
                
                for i, q in enumerate(unique_questions, 1):
                    q["id"] = i
                
                self._set_cached_questions(user_id, career_path, difficulty, unique_questions)
                
                return {
                    "success": True,
                    "questions": unique_questions,
                    "source": "ai",
                    "meta": {"cached": False, "retry_used": retry_used, "session_id": session_id}
                }
            
            # AI failed, return fallback
            fallback = self._get_fallback_questions()
            return {
                "success": True,
                "questions": fallback,
                "source": "fallback",
                "meta": {"cached": False, "retry_used": retry_used, "session_id": session_id}
            }
        
        except Exception as e:
            logger.error(f"[InterviewService] Error: {e}")
            fallback = self._get_fallback_questions()
            return {
                "success": True,
                "questions": fallback,
                "source": "exception_fallback",
                "meta": {"cached": False, "retry_used": False, "session_id": session_id}
            }

    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        career_path: str,
    ) -> Dict[str, Any]:
        """Evaluate a user's interview answer."""
        try:
            from services import gemini_service
            
            result = await gemini_service.evaluate_interview_answer(
                question,
                answer,
                career_path
            )
            return result
        except Exception as e:
            logger.error(f"[InterviewService] Error evaluating: {e}")
            return {
                "success": False,
                "error": "evaluation_failed",
                "message": "Could not evaluate your answer. Please try again."
            }

    async def get_hint(
        self,
        question: str,
        career_path: str,
    ) -> Dict[str, str]:
        """Get a coaching hint for a question."""
        try:
            prompt = f"""You are an expert interview coach. For this question: 
'{question}' for a '{career_path}' role, provide:
1. What the interviewer looks for (2-3 points)
2. How to structure the answer
3. A short example (2-3 sentences)

Return ONLY JSON: {{"looking_for": "...", "structure": "...", "example": "..."}}"""
            
            response = await self._transport.generate(prompt)
            
            text = response.strip()
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            text = text.strip()
            
            result = json.loads(text)
            return result
        
        except Exception as e:
            logger.error(f"[InterviewService] Error getting hint: {e}")
            return {
                "looking_for": "Focus on demonstrating your skills and experience.",
                "structure": "Use STAR method (Situation, Task, Action, Result).",
                "example": "Start with a brief context, then describe your specific contribution."
            }

    # ── Private: cache operations ─────────────────────────────────────────────

    def _get_cache_key(self, user_id: str, career_path: str, difficulty: str) -> str:
        return f"{user_id}:{career_path}:{difficulty}"

    def _get_cached_questions(
        self,
        user_id: str,
        career_path: str,
        difficulty: str
    ) -> Optional[List[Dict]]:
        cache_key = self._get_cache_key(user_id, career_path, difficulty)
        
        if cache_key in self._questions_cache:
            timestamp, questions = self._questions_cache[cache_key]
            current_time = time.time()
            if current_time - timestamp <= self._config.questions_cache_ttl_seconds:
                self._questions_cache.move_to_end(cache_key)
                return questions
            else:
                del self._questions_cache[cache_key]
        
        return None

    def _set_cached_questions(
        self,
        user_id: str,
        career_path: str,
        difficulty: str,
        questions: List[Dict]
    ) -> None:
        cache_key = self._get_cache_key(user_id, career_path, difficulty)
        self._questions_cache[cache_key] = (time.time(), questions)
        
        while len(self._questions_cache) > self._config.max_cached_question_sets:
            oldest_key = next(iter(self._questions_cache))
            del self._questions_cache[oldest_key]

    # ── Private: throttling ───────────────────────────────────────────────────

    def _is_user_throttled(self, user_id: str) -> bool:
        current_time = time.time()
        
        if user_id in self._user_last_request_time:
            time_since_last = current_time - self._user_last_request_time[user_id]
            if time_since_last < self._config.user_throttle_seconds:
                return True
        
        self._user_last_request_time[user_id] = current_time
        return False

    # ── Private: question generation ──────────────────────────────────────────

    async def _call_gemini_for_questions(
        self,
        profile: Dict[str, Any],
        career_path: str,
        difficulty: str,
        resume_text: str,
        personality: str,
        interview_mode: str,
    ) -> Optional[List[Dict]]:
        from services import gemini_service
        
        questions = await gemini_service.generate_interview_questions(
            profile,
            career_path,
            difficulty,
            resume_text,
            personality,
            interview_mode
        )
        
        if isinstance(questions, list) and len(questions) > 0:
            return questions
        
        return None

    def _deduplicate_questions(self, questions: List[Dict]) -> List[Dict]:
        seen = set()
        unique_questions = []
        
        for q in questions:
            question_text = q.get("question", "").strip().lower()
            if question_text and question_text not in seen:
                seen.add(question_text)
                unique_questions.append(q)
        
        return unique_questions

    # ── Private: fallback ─────────────────────────────────────────────────────

    def _get_fallback_questions(self) -> List[Dict]:
        return FALLBACK_QUESTIONS