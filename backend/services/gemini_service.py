"""
AI Service using Google Gemini 2.5 Flash (Free Tier)
6 calls combined into 1 using smart caching
"""
import os
import json
import re
import random
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Set this to True to bypass Gemini API calls and return realistic fake data
MOCK_MODE = False

MOCK_RESPONSE = {
    "analysis": {
        "experience_level": "Intermediate",
        "experience_reason": "Candidate has a strong foundation in Python and React with multiple projects showing full-stack capabilities.",
        "strengths": ["REST API development", "TypeScript/React expertise", "Database design", "System Architecture basics"],
        "weaknesses": ["Advanced data structures", "Microservices orchestration", "Kubernetes experience is limited"]
    },
    "career_paths": [
        {
            "name": "Full Stack Engineer",
            "match_percentage": 92,
            "reason": "Perfect alignment with existing React+FastAPI project portfolio."
        },
        {
            "name": "Backend Architect",
            "match_percentage": 85,
            "reason": "Strong logical structure in codebase and efficient database handling."
        },
        {
            "name": "Frontend Lead",
            "match_percentage": 78,
            "reason": "Deep understanding of component lifecycle and state management."
        }
    ],
    "skill_gaps": [
        {
            "skill": "Redis Caching",
            "have": False,
            "priority": 1,
            "resources": [
                "Official Redis Docs",
                "Learn Redis with Python (Hussain Nasser)"
            ]
        },
        {
            "skill": "Docker Containerization",
            "have": False,
            "priority": 2,
            "resources": [
                "Docker for Beginners (Udemy)",
                "Full Stack Containerization Guide"
            ]
        }
    ],
    "roadmap": {
        "target_career": "Full Stack Developer",
        "duration_months": 6,
        "total_weeks": 24,
        "milestones": [
            {
                "week": 1,
                "title": "FastAPI Masterclass",
                "description": "Deep dive into asynchronous programming and background tasks in Python.",
                "skills": ["Python", "FastAPI"],
                "deliverable": "Build a task queue processor"
            },
            {
                "week": 2,
                "title": "Frontend State Optimization",
                "description": "Implement advanced caching and TanStack Query for data fetching.",
                "skills": ["React", "React Query"],
                "deliverable": "Optimize existing jobs dashboard"
            },
            {
                "week": 4,
                "title": "Infrastructure & Docker",
                "description": "Learn to containerize and deploy with high availability.",
                "skills": ["Docker", "Nginx"],
                "deliverable": "Deploy project to a demo server"
            }
        ]
    }
}
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env file")

client_genai = genai.Client(api_key=GEMINI_API_KEY)

# Cache state to handle multiple calls in one session
_analysis_cache = {}
_last_github_data = {}
_last_leetcode_data = {}


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


def run_combined_analysis(
    github_data: dict,
    leetcode_data: dict,
    resume_text: str = "",
    user_profile: dict = {}
) -> dict:
    """
    Single combined Gemini API call.
    Replaces all 6 separate calls with 1.
    """
    if MOCK_MODE:
        return {"success": True, "data": MOCK_RESPONSE}

    prompt = f"""
You are an expert AI Career Mentor. Analyze this candidate 
profile completely and provide personalized career guidance.

===== USER PROFILE =====
User Type: {user_profile.get('user_type', 'Not specified')}

--- Education ---
College: {user_profile.get('college_name', 'Not specified')}
Degree: {user_profile.get('degree', 'Not specified')}
Branch: {user_profile.get('branch', 'Not specified')}
Year of Study: {user_profile.get('year_of_study', 'Not specified')}
Graduation Year: {user_profile.get('graduation_year', 'Not specified')}
CGPA: {user_profile.get('cgpa', 'Not specified')}

--- Professional ---
Current Job Title: {user_profile.get('current_job_title', 'Not specified')}
Current Company: {user_profile.get('current_company', 'Not specified')}
Years of Experience: {user_profile.get('years_of_experience', 'Not specified')}
Current Tech Stack: {user_profile.get('current_tech_stack', [])}
Reason for Switching: {user_profile.get('reason_for_switching', 'Not specified')}

--- Career Goals ---
Career Goal: {user_profile.get('career_goal', 'Not specified')}
Target Companies: {user_profile.get('target_companies', [])}
Preferred Work Type: {user_profile.get('preferred_work_type', 'Not specified')}
Job Search Timeline: {user_profile.get('job_search_timeline', 'Not specified')}

--- Skills ---
Extra Skills: {user_profile.get('extra_skills', [])}
Certificates: {user_profile.get('certificates', [])}

===== GITHUB DATA =====
{json.dumps(github_data or {}, indent=2)}

===== LEETCODE DATA =====
{json.dumps(leetcode_data or {}, indent=2)}

===== RESUME =====
{resume_text[:3000] if resume_text else "Not provided"}

===== YOUR TASK =====
Analyze ALL the above data including the user profile, 
GitHub activity, LeetCode performance, and resume.
Give PERSONALIZED recommendations based on their specific 
career goal, experience level, and background.
If career_goal is specified, make it the PRIMARY career path.

Use this exact structure:
{{
    "analysis": {{
        "strengths": [
            "strength 1",
            "strength 2",
            "strength 3",
            "strength 4",
            "strength 5"
        ],
        "weaknesses": [
            "weakness 1",
            "weakness 2",
            "weakness 3"
        ],
        "experience_level": "Beginner",
        "experience_reason": "Brief explanation here"
    }},
    "career_paths": [
        {{
            "name": "Career Path Name",
            "match_percentage": 90,
            "reason": "Why this fits the candidate"
        }},
        {{
            "name": "Career Path Name",
            "match_percentage": 80,
            "reason": "Why this fits the candidate"
        }},
        {{
            "name": "Career Path Name",
            "match_percentage": 70,
            "reason": "Why this fits the candidate"
        }}
    ],
    "skill_gaps": [
        {{
            "skill": "Skill Name",
            "have": false,
            "priority": 1,
            "resources": [
                "Resource 1",
                "Resource 2"
            ]
        }},
        {{
            "skill": "Skill Name",
            "have": true,
            "priority": 2,
            "resources": [
                "Resource 1",
                "Resource 2"
            ]
        }}
    ],
    "roadmap": {{
        "target_career": "Same as top career path name",
        "duration_months": 6,
        "total_weeks": 24,
        "milestones": [
            {{
                "week": 1,
                "title": "Milestone Title",
                "description": "What to accomplish this week",
                "skills": ["skill1", "skill2"],
                "deliverable": "What to build or achieve"
            }},
            {{
                "week": 2,
                "title": "Milestone Title",
                "description": "What to accomplish this week",
                "skills": ["skill1", "skill2"],
                "deliverable": "What to build or achieve"
            }}
        ]
    }}
}}
"""
    try:
        raw_text = _generate(prompt)
        clean_text = _clean_json(raw_text)
        result = json.loads(clean_text)
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse AI response: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Gemini API error: {str(e)}"
        }


def _get_cached_analysis(
    github_data: dict,
    leetcode_data: dict,
    resume_text: str = "",
    user_profile: dict = {}
) -> dict:
    global _last_github_data, _last_leetcode_data
    
    # Store the most recent inputs
    if github_data: _last_github_data = github_data
    if leetcode_data: _last_leetcode_data = leetcode_data
    
    cache_key = str(github_data) + str(leetcode_data) + str(resume_text[:100]) + str(user_profile)

    if cache_key not in _analysis_cache:
        result = run_combined_analysis(
            github_data,
            leetcode_data,
            resume_text,
            user_profile
        )
        if result["success"]:
            _analysis_cache[cache_key] = result["data"]
        else:
            return None, result["error"]

    return _analysis_cache[cache_key], None


# ============================================================
# THESE FUNCTIONS KEEP THE SAME NAMES AND SIGNATURES AS BEFORE
# The router does not need any changes at all
# ============================================================

def analyze_profile(
    github_data: dict,
    leetcode_data: dict,
    resume_text: str = "",
    user_profile: dict = {}
) -> dict:
    data, error = _get_cached_analysis(
        github_data,
        leetcode_data,
        resume_text,
        user_profile
    )
    if data:
        return data.get("analysis", {
            "strengths": [],
            "weaknesses": [],
            "experience_level": "Intermediate",
            "experience_reason": "Analysis completed"
        })
    return {
        "error": error or "Analysis failed",
        "strengths": ["Error in analysis"],
        "weaknesses": [],
        "experience_level": "Intermediate",
        "experience_reason": "Could not complete analysis"
    }


def generate_career_paths(
    analysis: dict,
    github_data: dict,
    leetcode_data: dict,
    resume_text: str = "",
    user_profile: dict = {}
) -> list:
    data, error = _get_cached_analysis(
        github_data,
        leetcode_data,
        resume_text,
        user_profile
    )
    if data:
        return data.get("career_paths", [])
    return [{"error": error or "Failed to generate career paths"}]


def generate_skill_gaps(
    analysis: dict,
    career_path: str,
    github_data: dict,
    resume_text: str = "",
    user_profile: dict = {}
) -> list:
    data, error = _get_cached_analysis(
        github_data=_last_github_data,
        leetcode_data=_last_leetcode_data,
        resume_text=resume_text,
        user_profile=user_profile
    )
    if data:
        return data.get("skill_gaps", [])
    return [{"error": error or "Failed to generate skill gaps"}]


def generate_roadmap(
    analysis: dict,
    career_path: str,
    duration_months: int = 6,
    resume_text: str = "",
    user_profile: dict = {}
) -> dict:
    data, error = _get_cached_analysis(
        github_data=_last_github_data,
        leetcode_data=_last_leetcode_data,
        resume_text=resume_text,
        user_profile=user_profile
    )
    if data:
        return data.get("roadmap", {
            "target_career": career_path,
            "duration_months": duration_months,
            "milestones": []
        })
    return {
        "error": error or "Failed to generate roadmap",
        "target_career": career_path,
        "duration_months": duration_months,
        "milestones": []
    }


def generate_interview_questions(
    profile: dict,
    career_path: str,
    difficulty: str,
    resume_text: str = "",
    personality: str = "friendly"
) -> list:
    # Build personality instruction based on the selected mode
    if personality == "friendly":
        personality_instruction = """
    You are a warm, encouraging interviewer. 
    Ask questions in a supportive tone.
    Use phrases like "Great topic! Tell me about..."
    """
    elif personality == "strict":
        personality_instruction = """
    You are a strict, no-nonsense interviewer.
    Ask direct, challenging questions with no hints.
    Use phrases like "Explain exactly how...", "Be specific about..."
    """
    elif personality == "google":
        personality_instruction = """
    You are a Google-style technical interviewer.
    Ask deep, pressure-filled questions about system design,
    scalability, algorithms, and edge cases.
    Use phrases like "Now consider if this scaled to 1 million users..."
    """
    else:
        personality_instruction = ""

    prompt = f"""You are an expert technical interviewer.
{personality_instruction}

Session ID: {random.randint(10000, 99999)}
Timestamp: {int(time.time())}
Generate FRESH unique questions - do not repeat previous sessions.

Generate exactly 5 interview questions for: {career_path}
Difficulty: {difficulty}
Profile: {json.dumps(profile)}
{f"Resume highlights: {resume_text[:500]}" if resume_text else ""}

Return ONLY a JSON array with exactly 5 objects.
Each object must have:
"id" (number 1-5),
"question" (string),
"type" (technical/behavioral/dsa/system_design/project_based),
"difficulty" (string),
"hint" (string)

Return ONLY the JSON array, no other text."""
    try:
        text = _generate(prompt)
        questions = json.loads(_clean_json(text))
        if isinstance(questions, list) and len(questions) > 0:
            return questions
        return []
    except Exception as e:
        print(f"Gemini attempt 1 failed: {str(e)}, retrying...")
        try:
            # Retry once with simpler prompt
            simple_prompt = f"""Generate exactly 5 interview questions for {career_path} role.
Difficulty: {difficulty}
Return ONLY a JSON array with 5 objects.
Each object must have:
"id" (number 1-5),
"question" (string),
"type" (technical/behavioral/dsa/system_design/project_based),
"difficulty" (string),
"hint" (string)
Return ONLY the JSON array, no other text."""
            text = _generate(simple_prompt)
            questions = json.loads(_clean_json(text))
            if isinstance(questions, list) and len(questions) > 0:
                return questions
            return []
        except Exception as e2:
            print(f"Gemini attempt 2 also failed: {str(e2)}")
            return []


def evaluate_interview_answer(
    question: str,
    answer: str,
    career_path: str
) -> dict:
    prompt = f"""You are an expert technical interviewer for {career_path}.

Question: {question}
Candidate Answer: {answer}

Return ONLY valid JSON with exactly these fields:
"score" (number 1-10),
"good_points" (array of 2-3 strings),
"missing_points" (array of 2-3 strings),
"model_answer" (string, 2-3 sentences),
"tip" (string, one specific tip)

No markdown, no extra text, just JSON."""
    try:
        return json.loads(_clean_json(_generate(prompt)))
    except Exception:
        return {
            "score": 5,
            "good_points": ["Attempted the question"],
            "missing_points": ["Could not evaluate properly"],
            "model_answer": "Please try again",
            "tip": "Be more specific in your answers"
        }
