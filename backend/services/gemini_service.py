"""
AI Service using Google Gemini 1.5 Flash (Free Tier)
Handles all AI-powered analysis
"""
import os
import json
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env file")

client_genai = genai.Client(api_key=GEMINI_API_KEY)


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    if text.startswith('['):
        depth = 0
        for i, c in enumerate(text):
            if c == '[': depth += 1
            elif c == ']': depth -= 1
            if depth == 0:
                text = text[:i+1]
                break
    elif text.startswith('{'):
        depth = 0
        for i, c in enumerate(text):
            if c == '{': depth += 1
            elif c == '}': depth -= 1
            if depth == 0:
                text = text[:i+1]
                break
    return text.strip()


def _generate(prompt: str) -> str:
    response = client_genai.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


def analyze_profile(github_data: dict, leetcode_data: dict, resume_text: str = "") -> dict:
    prompt = f"""
    You are an expert career analyst. Analyze the following profile data and provide career insights.
    
    GITHUB DATA:
    {json.dumps(github_data, indent=2)}
    
    LEETCODE DATA:
    {json.dumps(leetcode_data, indent=2)}
    
    {f"RESUME DATA:{resume_text[:2000]}" if resume_text else ""}
    
    Provide a JSON response with:
    1. "strengths": Array of 5-7 key technical strengths
    2. "weaknesses": Array of 3-5 areas for improvement
    3. "experience_level": One of "Beginner", "Intermediate", or "Advanced"
    4. "experience_reason": Brief explanation
    
    Return ONLY valid JSON, no markdown formatting.
    """
    try:
        return json.loads(_clean_json(_generate(prompt)))
    except Exception as e:
        return {
            "error": f"Analysis failed: {str(e)}",
            "strengths": ["Error in analysis"],
            "weaknesses": [],
            "experience_level": "Intermediate",
            "experience_reason": "Could not complete analysis"
        }


def generate_career_paths(analysis: dict, github_data: dict, leetcode_data: dict, resume_text: str = "") -> list:
    prompt = f"""
    You are an expert career counselor. Recommend career paths based on this profile.
    
    USER ANALYSIS:
    {json.dumps(analysis, indent=2)}
    
    GITHUB DATA:
    {json.dumps(github_data, indent=2)}
    
    {f"RESUME DATA:{resume_text[:2000]}" if resume_text else ""}
    
    Recommend 3-5 career paths. For each provide:
    - "name": Career path name
    - "match_percentage": 0-100 match score (must be a number)
    - "reason": Why this path fits their profile
    
    Return ONLY valid JSON array, no markdown formatting.
    """
    try:
        paths = json.loads(_clean_json(_generate(prompt)))
        if isinstance(paths, dict) and "career_paths" in paths:
            return paths["career_paths"]
        return paths
    except Exception as e:
        return [{"error": f"Failed to generate career paths: {str(e)}"}]


def generate_skill_gaps(analysis: dict, career_path: str, github_data: dict, resume_text: str = "") -> list:
    current_skills = []
    if isinstance(github_data, dict):
        lang_stats = github_data.get("language_stats", {})
        current_skills = list(lang_stats.keys())[:10]

    prompt = f"""
    You are an expert tech recruiter. Analyze skill gaps for someone wanting to become a {career_path}.
    
    CURRENT SKILLS: {current_skills}
    USER ANALYSIS: {json.dumps(analysis, indent=2)}
    TARGET CAREER: {career_path}
    {f"RESUME DATA:{resume_text[:1000]}" if resume_text else ""}
    
    Provide a JSON array of skills with:
    - "skill": Skill name
    - "have": true if user likely has it, false if missing
    - "priority": 1-5 (1 = most important to learn first)
    - "resources": Array of 2-3 learning resources
    
    Return ONLY valid JSON array, no markdown formatting.
    """
    try:
        return json.loads(_clean_json(_generate(prompt)))
    except Exception as e:
        return [{"error": f"Failed to generate skill gaps: {str(e)}"}]


def generate_roadmap(analysis: dict, career_path: str, duration_months: int = 6, resume_text: str = "") -> dict:
    prompt = f"""
    You are an expert career coach. Create a roadmap for someone to become a {career_path}.
    
    USER ANALYSIS: {json.dumps(analysis, indent=2)}
    TARGET CAREER: {career_path}
    DURATION: {duration_months} months
    {f"RESUME DATA:{resume_text[:1000]}" if resume_text else ""}
    
    Provide JSON with:
    - "target_career": The career path
    - "duration_months": Total duration
    - "total_weeks": Calculated weeks
    - "milestones": Array of milestones, each with:
      - "week": Week number
      - "title": Short milestone title
      - "description": What to accomplish
      - "skills": Array of skills to learn
      - "deliverable": What to build or achieve
    
    Use simple English without special characters.
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


def generate_interview_questions(profile: dict, career_path: str, difficulty: str, resume_text: str = "") -> list:
    prompt = f"""You are an expert technical interviewer.

Generate exactly 5 interview questions for a candidate applying for: {career_path}
Difficulty level: {difficulty}

Candidate profile:
- Skills: {profile.get('extra_skills', [])}
- Experience: {profile.get('experience', [])}
- College: {profile.get('college_name', 'Not specified')}
- Career Goal: {profile.get('career_goal', career_path)}
{f"- Resume highlights: {resume_text[:500]}" if resume_text else ""}

Return ONLY a JSON array with exactly 5 objects. Each object must have:
"id" (number 1-5), "question" (string), "type" (one of: technical, behavioral, dsa, system_design, project_based), "difficulty" (string), "hint" (string)

Return ONLY the JSON array, no other text."""
    try:
        text = _generate(prompt)
        questions = json.loads(_clean_json(text))
        if isinstance(questions, list) and len(questions) > 0:
            return questions
        return []
    except Exception as e:
        return [
            {"id": 1, "question": f"Tell me about your experience with {career_path}", "type": "behavioral", "difficulty": difficulty, "hint": "Focus on specific projects"},
            {"id": 2, "question": "What are the SOLID principles?", "type": "technical", "difficulty": difficulty, "hint": "There are 5 principles"},
            {"id": 3, "question": "Explain your most challenging project", "type": "project_based", "difficulty": difficulty, "hint": "Mention the problem, solution, and outcome"},
            {"id": 4, "question": "How would you design a URL shortener?", "type": "system_design", "difficulty": difficulty, "hint": "Think about scalability"},
            {"id": 5, "question": "Reverse a linked list", "type": "dsa", "difficulty": difficulty, "hint": "Think about iterative vs recursive approach"}
        ]


def evaluate_interview_answer(question: str, answer: str, career_path: str) -> dict:
    prompt = f"""You are an expert technical interviewer evaluating a candidate for {career_path}.

Question: {question}
Candidate Answer: {answer}

Evaluate and provide JSON with:
- "score": number from 1-10
- "good_points": array of 2-3 things done well
- "missing_points": array of 2-3 things missing or could improve
- "model_answer": a brief model answer (2-3 sentences)
- "tip": one specific tip for improvement

Return ONLY valid JSON, no markdown formatting."""
    try:
        return json.loads(_clean_json(_generate(prompt)))
    except Exception as e:
        return {
            "score": 5,
            "good_points": ["Attempted the question"],
            "missing_points": ["Could not evaluate properly"],
            "model_answer": "Please try again",
            "tip": "Be more specific in your answers"
        }
