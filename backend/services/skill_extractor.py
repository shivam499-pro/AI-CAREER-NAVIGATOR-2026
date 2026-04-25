"""
Skill Extractor Service
AI-powered extraction of skills from resumes, job descriptions, and profiles.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from supabase import create_client

logger = logging.getLogger(__name__)


# Skill categories and related keywords
SKILL_CATEGORIES = {
    "programming_languages": [
        "python", "javascript", "java", "typescript", "c++", "c#", "go", "rust", 
        "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl", "shell"
    ],
    "web_technologies": [
        "react", "vue", "angular", "next.js", "node.js", "express", "django", 
        "flask", "fastapi", "spring", "asp.net", "html", "css", "sass", "tailwind"
    ],
    "databases": [
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", 
        "oracle", "sqlite", "dynamodb", "cassandra", "firebase"
    ],
    "cloud_infrastructure": [
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
        "cloudformation", "jenkins", "ci/cd", "devops"
    ],
    "data_science": [
        "machine learning", "deep learning", "tensorflow", "pytorch", "pandas",
        "numpy", "scikit-learn", "nlp", "computer vision", "data analysis",
        "statistics", "data visualization", "tableau", "power bi"
    ],
    "ai_ml": [
        "artificial intelligence", "llm", "gpt", "chatgpt", "transformers",
        "bert", "prompt engineering", "ai", "neural networks", "reinforcement learning"
    ],
    "soft_skills": [
        "leadership", "communication", "teamwork", "problem-solving", "analytical",
        "project management", "agile", "scrum", "presentation", "mentoring"
    ],
    "tools": [
        "git", "github", "gitlab", "jira", "confluence", "notion", "slack",
        "figma", "photoshop", "illustrator", "excel", "powerpoint"
    ]
}


class SkillExtractor:
    """
    Extract and categorize skills from text using keyword matching and AI.
    """
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        self._supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
    
    async def extract_from_resume(self, resume_text: str) -> dict:
        """
        Extract skills from resume text.
        
        Returns:
            dict with extracted skills organized by category
        """
        text_lower = resume_text.lower()
        
        extracted_skills = {}
        
        for category, keywords in SKILL_CATEGORIES.items():
            found_skills = []
            for skill in keywords:
                # Check for exact match or word boundary
                if skill in text_lower:
                    found_skills.append(skill)
            
            if found_skills:
                extracted_skills[category] = list(set(found_skills))
        
        # Get unique skills count
        all_skills = []
        for skills in extracted_skills.values():
            all_skills.extend(skills)
        
        return {
            "skills": extracted_skills,
            "total_count": len(all_skills),
            "extracted_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def extract_from_job_description(self, job_text: str) -> dict:
        """
        Extract required and preferred skills from job description.
        
        Returns:
            dict with required and preferred skills
        """
        text_lower = job_text.lower()
        
        required_skills = []
        preferred_skills = []
        
        # Extract all skills
        for category, keywords in SKILL_CATEGORIES.items():
            for skill in keywords:
                if skill in text_lower:
                    required_skills.append(skill)
        
        # Try to identify preferred skills (nice to have, plus, preferred)
        nice_to_have_keywords = ["preferred", "nice to have", "plus", "bonus"]
        for keyword in nice_to_have_keywords:
            if keyword in text_lower:
                # This would need more sophisticated parsing
                # For now, mark all as required
                break
        
        return {
            "required_skills": list(set(required_skills)),
            "preferred_skills": list(set(preferred_skills)),
            "extracted_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def extract_with_ai(self, text: str, user_id: Optional[str] = None) -> dict:
        """
        Use AI to extract skills with better accuracy.
        
        Args:
            text: Text to extract skills from
            user_id: Optional user ID for context
        
        Returns:
            dict with AI-extracted skills
        """
        # First do keyword extraction
        basic_result = await self.extract_from_resume(text)
        
        # Then enhance with AI
        try:
            import google.genai as genai
            
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return basic_result
            
            client = genai.Client(api_key=api_key)
            
            prompt = f"""Extract all technical skills, soft skills, tools, and technologies 
            mentioned in the following text. Return as a JSON list of skill names only.
            Do not add explanations or categories. Just list the skills.
            
            Text: {text[:5000]}"""
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            # Parse AI response
            ai_skills = []
            for line in response.text.split('\n'):
                line = line.strip().strip('-*').strip()
                if line and not line.startswith('{'):
                    ai_skills.append(line.lower())
            
            # Merge with basic extraction
            all_skills = set()
            for skills in basic_result["skills"].values():
                all_skills.update(skills)
            all_skills.update(ai_skills)
            
            return {
                "skills": basic_result["skills"],
                "ai_enhanced_skills": list(all_skills),
                "total_count": len(all_skills),
                "extracted_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.warning(f"AI skill extraction failed: {e}")
            return basic_result
    
    async def compare_skills(self, resume_skills: list, job_skills: list) -> dict:
        """
        Compare resume skills with job requirements.
        
        Returns:
            dict with match percentage and missing skills
        """
        resume_set = set(s.lower() for s in resume_skills)
        job_set = set(s.lower() for s in job_skills)
        
        matched = resume_set.intersection(job_set)
        missing = job_set - resume_set
        extra = resume_set - job_set
        
        match_percentage = 0
        if job_set:
            match_percentage = (len(matched) / len(job_set)) * 100
        
        return {
            "match_percentage": round(match_percentage, 1),
            "matched_skills": list(matched),
            "missing_skills": list(missing),
            "extra_resume_skills": list(extra),
            "matched_count": len(matched),
            "missing_count": len(missing)
        }
    
    async def get_skill_gaps(self, current_skills: list, target_role: str) -> dict:
        """
        Identify skill gaps for target role.
        
        Returns:
            dict with skills to learn
        """
        # Get job description for target role
        # This would ideally come from a database of role requirements
        
        target_skills = []
        
        # Match based on role keywords
        role_lower = target_role.lower()
        
        if "engineer" in role_lower:
            target_skills.extend(SKILL_CATEGORIES["programming_languages"])
            target_skills.extend(SKILL_CATEGORIES["web_technologies"])
            target_skills.extend(SKILL_CATEGORIES["databases"])
        
        if "data" in role_lower or "analyst" in role_lower:
            target_skills.extend(SKILL_CATEGORIES["data_science"])
            target_skills.extend(["sql", "python", "excel"])
        
        if "manager" in role_lower:
            target_skills.extend(SKILL_CATEGORIES["soft_skills"])
        
        current_set = set(s.lower() for s in current_skills)
        target_set = set(target_skills)
        
        gaps = target_set - current_set
        
        return {
            "target_role": target_role,
            "skills_to_learn": list(gaps),
            "priority_skills": list(gaps)[:5],  # Top 5 priorities
            "current_skill_count": len(current_set),
            "target_skill_count": len(target_set),
            "gap_count": len(gaps)
        }


# Global instance
skill_extractor = SkillExtractor()


# Convenience functions
async def extract_resume_skills(resume_text: str) -> dict:
    """Extract skills from resume text."""
    return await skill_extractor.extract_from_resume(resume_text)


async def ai_extract_skills(text: str, user_id: Optional[str] = None) -> dict:
    """Extract skills using AI enhancement."""
    return await skill_extractor.extract_with_ai(text, user_id)


async def compare_resume_to_job(resume_skills: list, job_description: str) -> dict:
    """Compare resume skills to job requirements."""
    job_result = await skill_extractor.extract_from_job_description(job_description)
    return await skill_extractor.compare_skills(resume_skills, job_result["required_skills"])
