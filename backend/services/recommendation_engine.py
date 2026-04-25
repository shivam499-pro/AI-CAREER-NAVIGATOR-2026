"""
Recommendation Engine Service
AI-powered job and career recommendations based on user profiles, skills, and market data.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from supabase import create_client

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Generates personalized recommendations for jobs, skills, and career paths.
    """
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        self._supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
    
    async def recommend_jobs(
        self,
        user_id: str,
        skills: list[str],
        experience_level: str = "mid",
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 10
    ) -> dict:
        """
        Recommend jobs based on user skills and preferences.
        
        Args:
            user_id: User ID
            skills: User's skills list
            experience_level: Experience level (entry, mid, senior, lead)
            location: Preferred location
            remote_only: Only remote jobs
            limit: Max recommendations
        
        Returns:
            dict with job recommendations
        """
        skill_set = set(s.lower() for s in skills)
        
        # Score each potential job
        jobs = await self._fetch_potential_jobs(location, remote_only, limit * 3)
        
        scored_jobs = []
        for job in jobs:
            job_skills = set(s.lower() for s in job.get("required_skills", []))
            
            # Calculate match score
            matched_skills = skill_set.intersection(job_skills)
            match_score = len(matched_skills) / len(job_skills) * 100 if job_skills else 0
            
            # Experience level check
            exp_match = self._check_experience_level(job.get("experience_level"), experience_level)
            
            if match_score > 0 or exp_match:
                scored_jobs.append({
                    "job": job,
                    "match_score": round(match_score, 1),
                    "matched_skills": list(matched_skills),
                    "experience_match": exp_match,
                    "score": round(match_score * 0.7 + (exp_match * 30), 1)
                })
        
        # Sort by score and return top recommendations
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "user_id": user_id,
            "recommendations": scored_jobs[:limit],
            "total_found": len(scored_jobs),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def recommend_skills_to_learn(
        self,
        user_id: str,
        current_skills: list[str],
        target_role: str
    ) -> dict:
        """
        Recommend skills to learn based on target role.
        
        Returns:
            dict with skill recommendations
        """
        from services.market_analyzer import market_analyzer
        
        current_set = set(s.lower() for s in current_skills)
        
        # Get role analysis
        role_analysis = await market_analyzer.analyze_role_demand(target_role)
        
        # Categorize skills
        already_have = current_set.copy()
        to_learn_high = [s for s in role_analysis["high_demand_skills"] if s.lower() not in current_set]
        to_learn_growing = [s for s in role_analysis["growing_skills"] if s.lower() not in current_set]
        
        # Priority ranking
        recommendations = []
        
        for skill in to_learn_high[:5]:
            trend = await market_analyzer.get_skill_trend(skill)
            recommendations.append({
                "skill": skill,
                "category": "high_demand",
                "priority": "high",
                "trend": trend.get("trend", "unknown"),
                "reason": "High demand skill for your target role"
            })
        
        for skill in to_learn_growing[:3]:
            trend = await market_analyzer.get_skill_trend(skill)
            recommendations.append({
                "skill": skill,
                "category": "growing",
                "priority": "medium",
                "trend": trend.get("trend", "unknown"),
                "reason": "Growing skill that can differentiate you"
            })
        
        return {
            "user_id": user_id,
            "target_role": target_role,
            "current_skill_count": len(current_skills),
            "recommendations": recommendations,
            "learning_path": [r["skill"] for r in recommendations],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def recommend_career_paths(
        self,
        user_id: str,
        current_role: str,
        skills: list[str],
        experience_years: int
    ) -> dict:
        """
        Recommend potential career paths based on current profile.
        
        Returns:
            dict with career path recommendations
        """
        from services.market_analyzer import market_analyzer
        
        skill_set = set(s.lower() for s in skills)
        
        # Define career progression paths
        paths = [
            {
                "role": "Senior Software Engineer",
                "skills_needed": ["system design", "architecture", "leadership"],
                "next_role": "Staff Engineer",
                "avg_salary": 150000
            },
            {
                "role": "Tech Lead",
                "skills_needed": ["team leadership", "project management", "architecture"],
                "next_role": "Engineering Manager",
                "avg_salary": 160000
            },
            {
                "role": "Full Stack Developer",
                "skills_needed": ["frontend", "backend", "devops"],
                "next_role": "Senior Full Stack",
                "avg_salary": 130000
            },
            {
                "role": "Data Scientist",
                "skills_needed": ["machine learning", "python", "sql"],
                "next_role": "Senior Data Scientist",
                "avg_salary": 140000
            },
            {
                "role": "DevOps Engineer",
                "skills_needed": ["kubernetes", "aws", "terraform"],
                "next_role": "Platform Engineer",
                "avg_salary": 145000
            }
        ]
        
        scored_paths = []
        for path in paths:
            needed = set(s.lower() for s in path["skills_needed"])
            match = skill_set.intersection(needed)
            match_score = len(match) / len(needed) * 100 if needed else 0
            
            scored_paths.append({
                "path": path,
                "match_score": round(match_score, 1),
                "matched_skills": list(match),
                "missing_skills": list(needed - skill_set)
            })
        
        scored_paths.sort(key=lambda x: x["match_score"], reverse=True)
        
        return {
            "user_id": user_id,
            "current_role": current_role,
            "experience_years": experience_years,
            "career_paths": scored_paths[:5],
            "recommended_path": scored_paths[0] if scored_paths else None,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def recommend_learning_resources(
        self,
        skill: str,
        level: str = "beginner"
    ) -> dict:
        """
        Recommend learning resources for a specific skill.
        
        Returns:
            dict with resource recommendations
        """
        resources = {
            "python": {
                "beginner": [
                    {"name": "Python.org Tutorial", "type": "documentation", "url": "https://docs.python.org/3/tutorial/"},
                    {"name": "Codecademy Python", "type": "course", "url": "https://www.codecademy.com/learn/learn-python-3"}
                ],
                "intermediate": [
                    {"name": "Real Python", "type": "tutorials", "url": "https://realpython.com"},
                    {"name": "Python Crash Course", "type": "book", "url": "https://nostarch.com/pythoncrashcourse2e"}
                ],
                "advanced": [
                    {"name": "Fluent Python", "type": "book", "url": "https://www.oreilly.com/library/view/fluent-python/9781491945937/"},
                    {"name": "Python Design Patterns", "type": "course", "url": "https://www.udemy.com/learn-python-design-patterns/"}
                ]
            },
            "react": {
                "beginner": [
                    {"name": "React Docs", "type": "documentation", "url": "https://react.dev"},
                    {"name": "React Tutorial", "type": "tutorial", "url": "https://react.dev/learn"}
                ],
                "intermediate": [
                    {"name": "React Patterns", "type": "guide", "url": "https://reactpatterns.com"},
                    {"name": "Epic React", "type": "course", "url": "https://epicreact.dev"}
                ],
                "advanced": [
                    {"name": "Advanced React Patterns", "type": "course", "url": "https://www.udemy.com/course/react-advanced-patterns/"},
                    {"name": "React Server Components", "type": "article", "url": "https://react.dev/blog"}
                ]
            }
        }
        
        skill_lower = skill.lower()
        level_key = level.lower() if level.lower() in ["beginner", "intermediate", "advanced"] else "beginner"
        
        return {
            "skill": skill,
            "level": level,
            "resources": resources.get(skill_lower, {}).get(level_key, []),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _fetch_potential_jobs(
        self,
        location: Optional[str],
        remote_only: bool,
        limit: int
    ) -> list:
        """Fetch potential jobs from database."""
        # This would query the jobs table
        # For now, return sample data structure
        return []
    
    def _check_experience_level(self, job_level: str, user_level: str) -> bool:
        """Check if job experience level matches user level."""
        if not job_level:
            return True
        
        levels = ["entry", "mid", "senior", "lead"]
        job_idx = levels.index(job_level.lower()) if job_level.lower() in levels else 1
        user_idx = levels.index(user_level.lower()) if user_level.lower() in levels else 1
        
        # Allow matching level or one level above
        return user_idx >= job_idx - 1


# Global instance
recommendation_engine = RecommendationEngine()


# Convenience functions
async def get_job_recommendations(
    user_id: str,
    skills: list[str],
    experience_level: str = "mid",
    location: Optional[str] = None,
    remote_only: bool = False,
    limit: int = 10
) -> dict:
    """Get job recommendations."""
    return await recommendation_engine.recommend_jobs(
        user_id, skills, experience_level, location, remote_only, limit
    )


async def get_skill_recommendations(
    user_id: str,
    current_skills: list[str],
    target_role: str
) -> dict:
    """Get skill recommendations."""
    return await recommendation_engine.recommend_skills_to_learn(
        user_id, current_skills, target_role
    )


async def get_career_paths(
    user_id: str,
    current_role: str,
    skills: list[str],
    experience_years: int
) -> dict:
    """Get career path recommendations."""
    return await recommendation_engine.recommend_career_paths(
        user_id, current_role, skills, experience_years
    )


async def get_learning_resources(skill: str, level: str = "beginner") -> dict:
    """Get learning resource recommendations."""
    return await recommendation_engine.recommend_learning_resources(skill, level)
