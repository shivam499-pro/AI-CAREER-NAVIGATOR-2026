"""
Analysis Data Models
Pydantic models for analysis results - Phase 1 LSP Fix
Enforces canonical field names regardless of AI response chaos.
"""
from typing import List, Optional, Any
from pydantic import BaseModel, model_validator
from datetime import datetime


class CareerPath(BaseModel):
    """Career path recommendation model.

    Normalizes chaotic AI field names:
    - career_name / title / name → name (canonical)
    - match / match_percentage   → match_percentage (canonical)
    - justification / reason     → reason (canonical)
    """
    name: str
    match_percentage: int
    reason: str

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if 'name' not in values or not values['name']:
                values['name'] = (
                    values.pop('career_name', None) or
                    values.pop('title', None) or
                    'Unknown'
                )
            if 'match_percentage' not in values:
                values['match_percentage'] = values.pop('match', 0)
            if 'reason' not in values or not values['reason']:
                values['reason'] = values.pop('justification', 'No reason provided')
        return values


class SkillGap(BaseModel):
    """Skill gap analysis model.

    Normalizes chaotic AI field names:
    - skill_name / name / skill → skill (canonical)
    - has / owned / have        → have (canonical)
    - priority_level / level    → priority (canonical)
    """
    skill: str
    have: bool
    priority: int
    resources: List[str] = []

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if 'skill' not in values or not values['skill']:
                values['skill'] = (
                    values.pop('skill_name', None) or
                    values.pop('name', None) or
                    'Unknown'
                )
            if 'have' not in values:
                values['have'] = (
                    values.pop('has', None) or
                    values.pop('owned', None) or
                    False
                )
            if 'priority' not in values:
                values['priority'] = (
                    values.pop('priority_level', None) or
                    values.pop('level', None) or
                    1
                )
        return values


class Milestone(BaseModel):
    """Roadmap milestone model."""
    week: int
    title: str
    description: str
    skills: List[str] = []
    completed: bool = False


class AnalysisResult(BaseModel):
    """Analysis result model with strict canonical schema."""
    id: str
    user_id: str
    strengths: List[str]
    weaknesses: List[str]
    experience_level: str  # Beginner, Intermediate, Advanced
    career_paths: List[CareerPath]
    skill_gaps: List[SkillGap]
    created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Normalize skill_gap → skill_gaps
            if 'skill_gaps' not in values and 'skill_gap' in values:
                values['skill_gaps'] = values.pop('skill_gap')
        return values


class Roadmap(BaseModel):
    """Career roadmap model."""
    id: str
    target_career: str
    duration_months: int
    milestones: List[Milestone]


class Job(BaseModel):
    """Job listing model."""
    id: str
    title: str
    company: str
    location: str
    type: str  # Full-time, Part-time, Internship
    url: str
    match_score: int