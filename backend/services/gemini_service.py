"""
AI Service using Groq (replaces Gemini)
Fast, free inference using Llama 3.1
"""
import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.1-8b-instant"


def _clean_json(text: str) -> str:
    import re
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    # Find the first complete JSON object or array
    # Try to extract just the JSON part
    text = text.strip()
    # Find start of JSON
    if text.startswith('['):
        # Find matching closing bracket
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
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def analyze_profile(github_data: dict, leetcode_data: dict, resume_text: str = "") -> dict:
    # Build resume section if available
    resume_section = ""
    if resume_text:
        resume_section = f"""
    RESUME DATA:
    {resume_text[:2000]}
    """
    
    prompt = f"""
    You are an expert career analyst. Analyze the following profile data and provide career insights.
    
    GITHUB DATA:
    {json.dumps(github_data, indent=2)}
    
    LEETCODE DATA:
    {json.dumps(leetcode_data, indent=2)}
    {resume_section}
    
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
    # Build resume section if available
    resume_section = ""
    if resume_text:
        resume_section = f"""
    RESUME DATA:
    {resume_text[:2000]}
    """
    
    prompt = f"""
    You are an expert career counselor. Recommend career paths based on this profile.
    
    USER ANALYSIS:
    {json.dumps(analysis, indent=2)}
    
    GITHUB DATA:
    {json.dumps(github_data, indent=2)}
    {resume_section}
    
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

    # Build resume section if available
    resume_section = ""
    if resume_text:
        resume_section = f"""
    RESUME DATA:
    {resume_text[:2000]}
    """
    
    prompt = f"""
    You are an expert tech recruiter. Analyze skill gaps for someone wanting to become a {career_path}.
    
    CURRENT SKILLS: {current_skills}
    USER ANALYSIS: {json.dumps(analysis, indent=2)}
    TARGET CAREER: {career_path}
    {resume_section}
    
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
    # Build resume section if available
    resume_section = ""
    if resume_text:
        resume_section = f"""
    RESUME DATA:
    {resume_text[:2000]}
    """
    
    prompt = f"""
    You are an expert career coach. Create a roadmap for someone to become a {career_path}.
    
    USER ANALYSIS: {json.dumps(analysis, indent=2)}
    TARGET CAREER: {career_path}
    DURATION: {duration_months} months
    {resume_section}
    
    Provide JSON with:
    - "target_career": The career path
    - "duration_months": Total duration
    - "total_weeks": Calculated weeks
    - "milestones": Array of milestones, each with:
      - "week": Week number
      - "title": Short milestone title
      - "description": What to accomplish
      - "skills": Array of skills to learn
      - "deliverable": What to build/achieve
    
    Important: In the milestones array, ensure all strings are properly quoted and there are no special characters or apostrophes in the text. Use simple English without contractions.
    Return ONLY valid JSON, no markdown formatting.
    """
    
    # Try with retry logic
    for attempt in range(2):
        try:
            response_text = _generate(prompt)
            roadmap = json.loads(_clean_json(response_text))
            
            # Validate roadmap has required fields
            if not isinstance(roadmap, dict):
                raise ValueError("Response is not a JSON object")
            
            if "duration_months" not in roadmap:
                roadmap["duration_months"] = duration_months
            if "total_weeks" not in roadmap:
                roadmap["total_weeks"] = duration_months * 4
            return roadmap
        except Exception as e:
            # If first attempt failed, try with simpler prompt
            if attempt == 0:
                simple_prompt = f"""
                Create a simple {duration_months} month roadmap to become a {career_path}. 
                Output ONLY valid JSON with this exact structure, no markdown:
                {{"target_career": "{career_path}", "duration_months": {duration_months}, "total_weeks": {duration_months * 4}, "milestones": [{{"week": 1, "title": "Title", "description": "Description", "skills": ["skill1"], "deliverable": "Deliverable"}}]}}
                """
                prompt = simple_prompt
                continue
            else:
                # Second attempt also failed
                return {
                    "error": f"Failed to generate roadmap: {str(e)}",
                    "target_career": career_path,
                    "duration_months": duration_months,
                    "milestones": []
                }
    
    # Fallback (should not reach here)
    return {
        "target_career": career_path,
        "duration_months": duration_months,
        "milestones": []
    }
