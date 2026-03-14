"""
Analysis Data Models
Pydantic models for analysis results
"""
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class CareerPath(BaseModel):
    """Career path recommendation model."""
    name: str
    match_percentage: int
    reason: str

class SkillGap(BaseModel):
    """Skill gap analysis model."""
    skill: str
    have: bool
    priority: int
    resources: List[str] = []

class Milestone(BaseModel):
    """Roadmap milestone model."""
    week: int
    title: str
    description: str
    skills: List[str] = []
    completed: bool = False

class AnalysisResult(BaseModel):
    """Analysis result model."""
    id: str
    user_id: str
    strengths: List[str]
    weaknesses: List[str]
    experience_level: str  # Beginner, Intermediate, Advanced
    career_paths: List[CareerPath]
    skill_gap: List[SkillGap]
    created_at: datetime

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
