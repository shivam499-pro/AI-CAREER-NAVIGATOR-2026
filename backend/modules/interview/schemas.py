from pydantic import BaseModel
from typing import Optional, List, Any


class GenerateQuestionsRequest(BaseModel):
    user_id: str
    career_path: str
    difficulty: str = "medium"
    personality: str = "friendly"
    interview_mode: str = "technical"


class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str
    career_path: str
    user_id: str


class SaveSessionRequest(BaseModel):
    user_id: str
    career_path: str
    questions: List[Any]
    answers: List[Any]
    scores: List[Any]
    total_score: float
    difficulty: Optional[str] = "medium"
    interview_mode: Optional[str] = "technical"
    is_simulation: Optional[bool] = False
    is_voice: Optional[bool] = False


class QuestionHintRequest(BaseModel):
    question: str
    career_path: str