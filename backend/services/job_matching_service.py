"""
Job Matching Service
AI-powered job matching engine that calculates meaningful match scores
using user profile and analysis data.
"""

from typing import List, Dict, Any, Optional
import re


# =============================================================================
# TECH SKILLS DATABASE
# =============================================================================

# Comprehensive list of tech skills for keyword matching
TECH_SKILLS = {
    # Programming Languages
    "python", "javascript", "java", "typescript", "go", "golang", "rust", "c++",
    "c#", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    
    # Frontend
    "react", "reactjs", "angular", "vue", "vuejs", "nextjs", "next.js",
    "html", "css", "sass", "less", "tailwind", "bootstrap", "redux",
    "graphql", "apollo", "webpack", "vite",
    
    # Backend
    "nodejs", "node.js", "express", "fastapi", "flask", "django", "spring",
    "rails", "laravel", "asp.net", ".net", "graphql", "rest", "grpc",
    
    # Databases
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "dynamodb", "cassandra", "oracle", "sqlite", "firebase", "supabase",
    
    # Cloud & DevOps
    "aws", "amazon web services", "azure", "gcp", "google cloud", "docker",
    "kubernetes", "k8s", "terraform", "ansible", "jenkins", "gitlab",
    "github actions", "circleci", "travis", "cloudformation",
    
    # Data Science & ML
    "machine learning", "ml", "deep learning", "tensorflow", "pytorch", "keras",
    "pandas", "numpy", "scikit-learn", "scipy", "jupyter", "spark", "hadoop",
    "data pipeline", "etl", "data warehouse", "tableau", "powerbi",
    
    # Mobile
    "ios", "android", "react native", "flutter", "xamarin", "cordova",
    "swiftui", "jetpack compose",
    
    # Testing
    "testing", "pytest", "junit", "selenium", "cypress", "jest", "mocha",
    "unittest", "testng", "playwright",
    
    # Other
    "git", "linux", "unix", "bash", "shell", "agile", "scrum",
    "rest api", "microservices", "ci/cd", "oauth", "jwt", "websocket"
}

# Common seniority/level keywords
EXPERIENCE_LEVELS = {
    "entry": ["intern", "internship", "entry", "junior", "jr", "fresher", "graduate", "trainee", "associate"],
    "mid": ["mid-level", "mid level", "software engineer", "developer", "programmer"],
    "senior": ["senior", "sr.", "lead", "principal", "staff", "architect", "head", "director", "manager"]
}

# Career goal keywords mapping
CAREER_GOAL_KEYWORDS = {
    "frontend": ["frontend", "front-end", "ui developer", "ui engineer", "react", "angular", "vue"],
    "backend": ["backend", "back-end", "server", "api", "python", "java", "node"],
    "fullstack": ["fullstack", "full stack", "full-stack", "mern", "mean"],
    "data_science": ["data scientist", "data engineer", "ml engineer", "machine learning", "ai"],
    "devops": ["devops", "sre", "site reliability", "cloud engineer", "infrastructure"],
    "mobile": ["mobile", "ios", "android", "react native", "flutter"],
    "product": ["product manager", "product owner", "pm"],
    "qa": ["qa", "tester", "quality assurance", "sdET"]
}


# =============================================================================
# SKILL EXTRACTION FUNCTIONS
# =============================================================================

def extract_skills_from_job(description: str) -> List[str]:
    """
    Extract technical skills from job description using keyword matching.
    
    Args:
        job_description: Job description text
        
    Returns:
        List of lowercase skill keywords found in the description
    """
    if not description:
        return []
    
    # Normalize text
    text = description.lower()
    
    # Find all matching skills
    found_skills = set()
    for skill in TECH_SKILLS:
        # Use word boundary matching to avoid partial matches
        # e.g., "java" should not match "javascript"
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text):
            found_skills.add(skill)
    
    return list(found_skills)


def normalize_user_skills(profile: Dict[str, Any], analysis: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Merge user skills from profile and analysis into a normalized list.
    
    Args:
        profile: User profile from profiles table
        analysis: Optional analysis data from analyses table
        
    Returns:
        Clean lowercase list of user skills
    """
    user_skills = set()
    
    # 1. Get tech stack from profile
    if profile and profile.get("current_tech_stack"):
        tech_stack = profile.get("current_tech_stack", [])
        if isinstance(tech_stack, list):
            for skill in tech_stack:
                if isinstance(skill, str):
                    user_skills.add(skill.lower().strip())
        elif isinstance(tech_stack, dict):
            # Handle JSONB object format
            for skill in tech_stack.values():
                if isinstance(skill, list):
                    for s in skill:
                        if isinstance(s, str):
                            user_skills.add(s.lower().strip())
                elif isinstance(skill, str):
                    user_skills.add(skill.lower().strip())
    
    # 2. Get extra_skills from profile
    if profile and profile.get("extra_skills"):
        extra_skills = profile.get("extra_skills", [])
        if isinstance(extra_skills, list):
            for skill in extra_skills:
                if isinstance(skill, str):
                    user_skills.add(skill.lower().strip())
    
    # 3. Get strengths from analysis
    if analysis and analysis.get("strengths"):
        strengths = analysis.get("strengths", [])
        if isinstance(strengths, list):
            for strength in strengths:
                if isinstance(strength, str):
                    # Check if it's a skill (contains tech keywords)
                    strength_lower = strength.lower()
                    for skill in TECH_SKILLS:
                        if skill in strength_lower:
                            user_skills.add(skill)
                    # Add full strength as skill
                    user_skills.add(strength_lower.strip())
    
    # 4. Get skill_gaps from analysis - these are skills to learn
    # We don't add them to user_skills, but we track them for matching
    
    return list(user_skills)


def determine_experience_level(job_title: str, description: str = "") -> str:
    """
    Determine the experience level required for a job.
    
    Args:
        job_title: Job title text
        description: Optional job description
        
    Returns:
        "entry", "mid", or "senior"
    """
    text = (job_title + " " + (description or "")).lower()
    
    # Check for seniority indicators
    for keyword in EXPERIENCE_LEVELS["senior"]:
        if keyword in text:
            return "senior"
    
    for keyword in EXPERIENCE_LEVELS["entry"]:
        if keyword in text:
            return "entry"
    
    return "mid"  # Default to mid-level


def extract_required_skills_from_title(title: str) -> List[str]:
    """
    Extract potential required skills from job title.
    
    Args:
        job_title: Job title
        
    Returns:
        List of skills found in title
    """
    text = title.lower()
    found_skills = []
    
    for skill in TECH_SKILLS:
        if skill in text:
            found_skills.append(skill)
    
    return found_skills


# =============================================================================
# MATCH SCORE CALCULATION
# =============================================================================

def calculate_skill_match_score(user_skills: List[str], job_skills: List[str]) -> float:
    """
    Calculate skill match percentage.
    
    Args:
        user_skills: List of user skills
        job_skills: List of job required skills
        
    Returns:
        Match percentage (0-100)
    """
    if not job_skills:
        return 50.0  # Neutral if no requirements specified
    
    user_skills_set = set(user_skills)
    job_skills_set = set(job_skills)
    
    matched = user_skills_set.intersection(job_skills_set)
    match_percentage = (len(matched) / len(job_skills_set)) * 100
    
    return round(match_percentage, 1)


def calculate_career_goal_match(profile: Dict[str, Any], job_title: str) -> float:
    """
    Calculate career goal alignment score.
    
    Args:
        profile: User profile with career_goal
        job_title: Job title to check alignment
        
    Returns:
        1.0 if aligned, 0.5 otherwise
    """
    if not profile:
        return 0.5
    
    career_goal = profile.get("career_goal", "")
    if not career_goal:
        return 0.5
    
    goal_lower = career_goal.lower()
    title_lower = job_title.lower()
    
    # Check which category the career goal belongs to
    for category, keywords in CAREER_GOAL_KEYWORDS.items():
        if any(kw in goal_lower for kw in keywords):
            # User wants this category, check if job matches
            if any(kw in title_lower for kw in keywords):
                return 1.0
            break
    
    # Also check job title for tech stack alignment
    for skill in TECH_SKILLS:
        if skill in goal_lower and skill in title_lower:
            return 1.0
    
    return 0.5  # No clear alignment


def calculate_experience_match(user_level: str, job_level: str) -> float:
    """
    Calculate experience level match.
    
    Args:
        user_level: User's experience level from analysis
        job_level: Required job level ("entry", "mid", "senior")
        
    Returns:
        Match score (0-100)
    """
    # Level hierarchy
    level_order = {"entry": 1, "mid": 2, "senior": 3}
    
    user_level_norm = user_level.lower().strip() if user_level else "mid"
    job_level_norm = job_level.lower().strip() if job_level else "mid"
    
    user_level_val = level_order.get(user_level_norm, 2)
    job_level_val = level_order.get(job_level_norm, 2)
    
    # Perfect match = 100
    if user_level_val == job_level_val:
        return 100.0
    
    # One level too high = 60 (underqualified)
    # One level too low = 80 (overqualified but acceptable)
    if user_level_val > job_level_val:
        return 60.0  # User is more senior than required
    else:
        return 80.0  # User is less senior but can grow into role


def calculate_skill_gap_penalty(job_skills: List[str], user_skills: List[str], 
                                 skill_gaps: List[str] = None) -> float:
    """
    Calculate penalty for missing critical skills.
    
    Args:
        job_skills: Skills required by job
        user_skills: User's current skills
        skill_gaps: Skills identified as gaps in analysis
        
    Returns:
        Penalty factor (0-1, lower is worse)
    """
    if not job_skills:
        return 0.0  # No penalty if no requirements
    
    job_skills_set = set(job_skills)
    user_skills_set = set(user_skills)
    
    missing_skills = job_skills_set - user_skills_set
    
    if not missing_skills:
        return 0.0  # No penalty, user has all skills
    
    # Check if missing skills are critical (in skill gaps or common skills)
    critical_skills = {"python", "javascript", "sql", "aws", "docker", "git", "react", "node"}
    missing_critical = missing_skills.intersection(critical_skills)
    
    # Penalty based on proportion of missing skills
    missing_ratio = len(missing_skills) / len(job_skills_set)
    
    # Additional penalty for critical missing skills
    if missing_critical:
        penalty = min(0.3, len(missing_critical) * 0.1)
    else:
        penalty = 0.0
    
    return penalty + (missing_ratio * 0.2)


def calculate_match_score(user: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive match score for a job.
    
    Uses weighted formula:
    - 40% skill match
    - 25% career goal match  
    - 20% experience level match
    - 15% skill gap penalty
    
    Args:
        user: Dict with profile, analysis, experience_level
        job: Job data with title, description, etc.
        
    Returns:
        Dict with match_score, matched_skills, missing_skills
    """
    profile = user.get("profile", {})
    analysis = user.get("analysis", {})
    experience_level = user.get("experience_level", "mid")
    
    # Extract job skills from title and description
    job_title = job.get("title", "")
    job_description = job.get("description", "") or job.get("desc", "") or ""
    
    job_skills = extract_skills_from_job(job_description)
    title_skills = extract_required_skills_from_title(job_title)
    all_job_skills = list(set(job_skills + title_skills))
    
    # Normalize user skills
    user_skills = normalize_user_skills(profile, analysis)
    
    # Get skill gaps from analysis
    skill_gaps = []
    if analysis and analysis.get("skill_gaps"):
        gaps_data = analysis.get("skill_gaps")
        if isinstance(gaps_data, list):
            skill_gaps = [str(g).lower() for g in gaps_data]
        elif isinstance(gaps_data, dict):
            for v in gaps_data.values():
                if isinstance(v, list):
                    skill_gaps.extend([str(s).lower() for s in v])
    
    # Calculate individual scores
    skill_score = calculate_skill_match_score(user_skills, all_job_skills)
    career_score = calculate_career_goal_match(profile, job_title) * 100
    exp_score = calculate_experience_match(experience_level, determine_experience_level(job_title, job_description))
    gap_penalty = calculate_skill_gap_penalty(all_job_skills, user_skills, skill_gaps)
    
    # Weighted final score
    final_score = (
        (skill_score * 0.40) +
        (career_score * 0.25) +
        (exp_score * 0.20) +
        ((1 - gap_penalty) * 100 * 0.15)
    )
    
    # Ensure score is within bounds
    final_score = max(0, min(100, final_score))
    
    # Determine matched and missing skills
    user_skills_set = set(user_skills)
    job_skills_set = set(all_job_skills)
    
    matched_skills = list(user_skills_set.intersection(job_skills_set))
    missing_skills = list(job_skills_set - user_skills_set)
    
    return {
        "match_score": round(final_score, 1),
        "matched_skills": matched_skills[:5],  # Limit to top 5
        "missing_skills": missing_skills[:5],   # Limit to top 5
        "skill_match_percentage": skill_score,
        "career_goal_aligned": career_score == 100,
        "experience_match": exp_score
    }


# =============================================================================
# MAIN MATCHING FUNCTION
# =============================================================================

def match_jobs(user: Dict[str, Any], jobs: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    """
    Match jobs to user profile and return sorted by match score.
    
    Args:
        user: User data dict with profile, analysis, experience_level
        jobs: List of job dictionaries from API
        limit: Maximum number of jobs to return
        
    Returns:
        List of jobs with added match data, sorted by match_score descending
    """
    if not jobs:
        return []
    
    # Limit jobs to avoid heavy computation
    jobs_to_process = jobs[:limit]
    
    matched_jobs = []
    
    for job in jobs_to_process:
        match_data = calculate_match_score(user, job)
        
        # Add match data to job object
        enhanced_job = {
            **job,
            "match_score": match_data["match_score"],
            "matched_skills": match_data["matched_skills"],
            "missing_skills": match_data["missing_skills"],
            "skill_match_percentage": match_data["skill_match_percentage"],
            "career_goal_aligned": match_data["career_goal_aligned"],
            "experience_match": match_data["experience_match"]
        }
        
        matched_jobs.append(enhanced_job)
    
    # Sort by match score descending
    matched_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    
    return matched_jobs


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_top_skills_missing(user_skills: List[str], job_skills: List[str], n: int = 5) -> List[str]:
    """
    Get the top N missing skills that are most important.
    
    Args:
        user_skills: User's current skills
        job_skills: Job required skills
        n: Number of skills to return
        
    Returns:
        List of most important missing skills
    """
    user_skills_set = set(user_skills)
    job_skills_set = set(job_skills)
    
    missing = list(job_skills_set - user_skills_set)
    
    # Prioritize common/important skills
    important = {"python", "javascript", "sql", "aws", "docker", "git", "react", "node", "java"}
    missing.sort(key=lambda x: x in important, reverse=True)
    
    return missing[:n]


def get_recommended_improvements(matched_job: Dict[str, Any]) -> List[str]:
    """
    Generate actionable improvement recommendations based on missing skills.
    
    Args:
        matched_job: Job with match data
        
    Returns:
        List of improvement suggestions
    """
    missing_skills = matched_job.get("missing_skills", [])
    recommendations = []
    
    skill_resources = {
        "python": "https://www.python.org/about/gettingstarted/",
        "javascript": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
        "react": "https://react.dev/learn",
        "aws": "https://aws.amazon.com/getting-started/",
        "docker": "https://docs.docker.com/get-started/",
        "sql": "https://www.w3schools.com/sql/",
        "git": "https://git-scm.com/book/en/v2",
        "kubernetes": "https://kubernetes.io/docs/tutorials/"
    }
    
    for skill in missing_skills[:3]:
        if skill in skill_resources:
            recommendations.append(f"Learn {skill}: {skill_resources[skill]}")
        else:
            recommendations.append(f"Practice {skill} through projects")
    
    return recommendations