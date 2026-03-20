"""
Google Gemini AI Service
Handles all AI-powered analysis and generation using Gemini API
Migrated from deprecated google.generativeai to google.genai
"""
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = "gemini-2.0-flash-lite"


def _clean_json(text: str) -> str:
    """Strip markdown code fences from Gemini response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _generate(prompt: str) -> str:
    """Single shared call to Gemini — all functions use this."""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=2048,
        ),
    )
    return response.text


def analyze_profile(github_data: dict, leetcode_data: dict) -> dict:
    """
    Analyze GitHub and LeetCode data to identify strengths, weaknesses, and experience level.
    """
    prompt = f"""
    You are an expert career analyst. Analyze the following profile data and provide career insights.
    
    GITHUB DATA:
    {json.dumps(github_data, indent=2)}
    
    LEETCODE DATA:
    {json.dumps(leetcode_data, indent=2)}
    
    Based on this data, provide a JSON response with:
    1. "strengths": Array of 5-7 key technical strengths based on the data
    2. "weaknesses": Array of 3-5 areas for improvement
    3. "experience_level": One of "Beginner", "Intermediate", or "Advanced"
    4. "experience_reason": Brief explanation of why you assigned this level
    
    Consider:
    - Number of repositories and stars (GitHub)
    - Languages used and their diversity
    - Problem solving skills (LeetCode)
    - Contest participation and rating
    - Overall activity and consistency
    
    Return ONLY valid JSON, no markdown formatting.
    """

    try:
        result = json.loads(_clean_json(_generate(prompt)))
        return result
    except Exception as e:
        return {
            "error": f"Analysis failed: {str(e)}",
            "strengths": ["Error in analysis"],
            "weaknesses": [],
            "experience_level": "Intermediate",
            "experience_reason": "Could not complete analysis"
        }


def generate_career_paths(analysis: dict, github_data: dict, leetcode_data: dict) -> list:
    """
    Generate career path recommendations based on analysis.
    """
    prompt = f"""
    You are an expert career counselor. Based on the following analysis, recommend the most suitable career paths.
    
    USER ANALYSIS:
    {json.dumps(analysis, indent=2)}
    
    GITHUB DATA (skills demonstrated):
    {json.dumps(github_data, indent=2)}
    
    LEETCODE DATA (problem solving):
    {json.dumps(leetcode_data, indent=2)}
    
    Recommend 3-5 career paths. For each provide:
    - "name": Career path name (e.g., "Full Stack Developer", "Data Scientist", "DevOps Engineer")
    - "match_percentage": 0-100 match score
    - "reason": Why this path fits their profile
    
    Consider their actual skills, not just what they say they want.
    Focus on careers that match their demonstrated abilities.
    
    Return ONLY valid JSON array, no markdown formatting.
    """

    try:
        paths = json.loads(_clean_json(_generate(prompt)))
        if isinstance(paths, dict) and "career_paths" in paths:
            return paths["career_paths"]
        return paths
    except Exception as e:
        return [{"error": f"Failed to generate career paths: {str(e)}"}]


def generate_skill_gaps(analysis: dict, career_path: str, github_data: dict) -> list:
    """
    Generate skill gap analysis for a target career.
    """
    current_skills = []
    if isinstance(github_data, dict):
        lang_stats = github_data.get("language_stats", {})
        current_skills = list(lang_stats.keys())[:10]

    prompt = f"""
    You are an expert tech recruiter. Analyze the skill gap for someone wanting to become a {career_path}.
    
    USER'S CURRENT SKILLS:
    {current_skills}
    
    USER ANALYSIS:
    {json.dumps(analysis, indent=2)}
    
    TARGET CAREER: {career_path}
    
    Provide a JSON array of skills with:
    - "skill": Skill name
    - "have": true if user likely has it, false if missing
    - "priority": 1-5 (1 = most important to learn first)
    - "resources": Array of 2-3 suggested learning resources (courses, projects, docs)
    
    Focus on practical skills that employers actually want.
    Return ONLY valid JSON array, no markdown formatting.
    """

    try:
        return json.loads(_clean_json(_generate(prompt)))
    except Exception as e:
        return [{"error": f"Failed to generate skill gaps: {str(e)}"}]


def generate_roadmap(analysis: dict, career_path: str, duration_months: int = 6) -> dict:
    """
    Generate a step-by-step career roadmap.
    """
    prompt = f"""
    You are an expert career coach. Create a detailed roadmap for someone to become a {career_path}.
    
    USER ANALYSIS:
    {json.dumps(analysis, indent=2)}
    
    TARGET CAREER: {career_path}
    DURATION: {duration_months} months
    
    Create a weekly milestone plan. Provide JSON with:
    - "target_career": The career path
    - "duration_months": Total duration
    - "total_weeks": Calculated weeks
    - "milestones": Array of weekly milestones, each with:
      - "week": Week number
      - "title": Short milestone title
      - "description": What to accomplish
      - "skills": Array of skills to learn
      - "deliverable": What to build/achieve
      
    Make it practical and actionable. Include specific projects to build.
    Return ONLY valid JSON, no markdown formatting.
    """

    try:
        roadmap = json.loads(_clean_json(_generate(prompt)))
        if "duration_months" not in roadmap:
            roadmap["duration_months"] = duration_months
        if "total_weeks" not in roadmap:
            roadmap["total_weeks"] = duration_months * 4
        return roadmap
    except Exception as e:
        return {
            "error": f"Failed to generate roadmap: {str(e)}",
            "target_career": career_path,
            "duration_months": duration_months,
            "milestones": []
        }