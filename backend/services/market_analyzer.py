"""
Market Analyzer Service
Analyzes job market trends, salary data, and in-demand skills.
"""
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from supabase import create_client

logger = logging.getLogger(__name__)


# In-demand skills by role category
SKILL_DEMAND = {
    "software_engineer": {
        "high_demand": ["python", "javascript", "react", "aws", "docker", "kubernetes"],
        "growing": ["rust", "go", "typescript", "next.js"],
        "stable": ["java", "c++", "sql", "git"]
    },
    "data_scientist": {
        "high_demand": ["python", "machine learning", "sql", "tensorflow"],
        "growing": ["pytorch", "llm", "prompt engineering", "data visualization"],
        "stable": ["statistics", "r", "tableau"]
    },
    "devops": {
        "high_demand": ["aws", "kubernetes", "docker", "terraform", "ci/cd"],
        "growing": ["argo cd", "helm", "istio"],
        "stable": ["jenkins", "linux", "bash"]
    },
    "frontend_developer": {
        "high_demand": ["react", "typescript", "javascript", "css"],
        "growing": ["next.js", "vue", "tailwind", "svelte"],
        "stable": ["angular", "html", "sass"]
    },
    "backend_developer": {
        "high_demand": ["python", "node.js", "postgresql", "docker"],
        "growing": ["go", "rust", "fastapi", "gRPC"],
        "stable": ["java", "spring", "django", "mysql"]
    }
}


class MarketAnalyzer:
    """
    Analyzes job market trends and provides insights.
    """
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        self._supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
    
    async def analyze_role_demand(self, role: str) -> dict:
        """
        Analyze demand for a specific role.
        
        Returns:
            dict with demand metrics
        """
        role_lower = role.lower().replace(" ", "_")
        
        # Find matching role category
        matched_category = None
        for category in SKILL_DEMAND:
            if category.replace("_", " ") in role_lower:
                matched_category = category
                break
        
        if not matched_category:
            matched_category = "software_engineer"  # Default
        
        category_data = SKILL_DEMAND.get(matched_category, SKILL_DEMAND["software_engineer"])
        
        return {
            "role": role,
            "category": matched_category,
            "high_demand_skills": category_data["high_demand"],
            "growing_skills": category_data["growing"],
            "stable_skills": category_data["stable"],
            "demand_score": self._calculate_demand_score(role),
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_demand_score(self, role: str) -> int:
        """Calculate a demand score (0-100) for a role."""
        # Simplified scoring based on keyword matching
        high_demand_roles = [
            "software engineer", "full stack", "frontend", "backend",
            "data scientist", "devops", "cloud", "machine learning"
        ]
        
        role_lower = role.lower()
        for i, high_role in enumerate(high_demand_roles):
            if high_role in role_lower:
                return 100 - (i * 10)  # Higher priority roles get higher scores
        
        return 50  # Default moderate demand
    
    async def get_market_trends(self, timeframe: str = "30d") -> dict:
        """
        Get market trends for the specified timeframe.
        
        Args:
            timeframe: Time period (7d, 30d, 90d)
        
        Returns:
            dict with market trends
        """
        days = int(timeframe.replace("d", ""))
        
        return {
            "timeframe": timeframe,
            "top_growing_skills": [
                {"skill": "rust", "growth": 45},
                {"skill": "go", "growth": 38},
                {"skill": "typescript", "growth": 35},
                {"skill": "react", "growth": 32},
                {"skill": "python", "growth": 28},
                {"skill": "kubernetes", "growth": 25},
                {"skill": "aws", "growth": 22},
                {"skill": "llm", "growth": 85},  # AI/ML especially high
                {"skill": "prompt engineering", "growth": 72},
                {"skill": "tensorflow", "growth": 18}
            ],
            "declining_skills": [
                {"skill": "perl", "decline": -15},
                {"skill": "cobol", "decline": -12},
                {"skill": "flash", "decline": -10}
            ],
            "salary_trends": {
                "software_engineer": {"avg": 120000, "range": "90000-180000"},
                "data_scientist": {"avg": 115000, "range": "85000-165000"},
                "devops": {"avg": 125000, "range": "95000-175000"},
                "frontend": {"avg": 105000, "range": "75000-150000"},
                "backend": {"avg": 115000, "range": "85000-160000"}
            },
            "remote_opportunity": {
                "high_demand": ["frontend", "backend", "full stack", "data scientist"],
                "moderate": ["devops", "qa", "mobile"],
                "low": ["embedded", "hardware"]
            },
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_skill_trend(self, skill: str) -> dict:
        """
        Get trend data for a specific skill.
        
        Returns:
            dict with skill trend information
        """
        skill_lower = skill.lower()
        
        # Check if skill is in our demand data
        for category_data in SKILL_DEMAND.values():
            if skill_lower in category_data["high_demand"]:
                return {
                    "skill": skill,
                    "demand": "high",
                    "trend": "growing",
                    "score": 85,
                    "advice": "This skill is in high demand. Consider emphasizing it."
                }
            elif skill_lower in category_data["growing"]:
                return {
                    "skill": skill,
                    "demand": "growing",
                    "trend": "up",
                    "score": 70,
                    "advice": "This skill is growing. Good time to learn or emphasize."
                }
            elif skill_lower in category_data["stable"]:
                return {
                    "skill": skill,
                    "demand": "stable",
                    "trend": "flat",
                    "score": 50,
                    "advice": "This is a stable skill. Keep it in your toolkit."
                }
        
        # Unknown skill
        return {
            "skill": skill,
            "demand": "unknown",
            "trend": "unknown",
            "score": 30,
            "advice": "Research this skill further for market insights."
        }
    
    async def compare_roles(self, roles: list[str]) -> dict:
        """
        Compare multiple roles side by side.
        
        Returns:
            dict with role comparisons
        """
        comparisons = []
        
        for role in roles:
            analysis = await self.analyze_role_demand(role)
            comparisons.append({
                "role": role,
                "demand_score": analysis["demand_score"],
                "top_skills": analysis["high_demand_skills"][:3]
            })
        
        # Sort by demand score
        comparisons.sort(key=lambda x: x["demand_score"], reverse=True)
        
        return {
            "roles": comparisons,
            "highest_demand": comparisons[0] if comparisons else None,
            "compared_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_career_advice(self, current_skills: list, target_role: str) -> dict:
        """
        Get personalized career advice based on skills and target role.
        
        Returns:
            dict with career advice
        """
        role_analysis = await self.analyze_role_demand(target_role)
        
        current_set = set(s.lower() for s in current_skills)
        
        # Calculate match
        high_demand_set = set(role_analysis["high_demand_skills"])
        match = current_set.intersection(high_demand_set)
        match_percentage = (len(match) / len(high_demand_set)) * 100 if high_demand_set else 0
        
        return {
            "target_role": target_role,
            "role_demand_score": role_analysis["demand_score"],
            "skill_match_percentage": round(match_percentage, 1),
            "matching_skills": list(match),
            "skills_to_develop": list(high_demand_set - current_set),
            "advice": self._generate_advice(role_analysis, match_percentage),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_advice(self, role_analysis: dict, match_percentage: float) -> str:
        """Generate career advice based on analysis."""
        if match_percentage >= 70:
            return f"You have strong skills for {role_analysis['role']} roles. Focus on advanced topics and leadership."
        elif match_percentage >= 40:
            return f"You're a good fit for {role_analysis['role']}. Fill in the missing high-demand skills to increase opportunities."
        else:
            return f"Consider learning {', '.join(role_analysis['high_demand_skills'][:3])} to break into {role_analysis['role']} roles."


# Global instance
market_analyzer = MarketAnalyzer()


# Convenience functions
async def get_role_demand(role: str) -> dict:
    """Get demand analysis for a role."""
    return await market_analyzer.analyze_role_demand(role)


async def get_trends(timeframe: str = "30d") -> dict:
    """Get market trends."""
    return await market_analyzer.get_market_trends(timeframe)


async def analyze_skill(skill: str) -> dict:
    """Get trend for a specific skill."""
    return await market_analyzer.get_skill_trend(skill)


async def get_personalized_advice(current_skills: list, target_role: str) -> dict:
    """Get career advice."""
    return await market_analyzer.get_career_advice(current_skills, target_role)
