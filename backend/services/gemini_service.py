"""
AI Service using Google Gemini 2.5 Flash (Free Tier)
6 calls combined into 1 using smart caching
"""
import os
import json
import re
import random
import time
from collections import OrderedDict
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Set this to True to bypass Gemini API calls and return realistic fake data
MOCK_MODE = False

# Retry configuration
MAX_RETRIES = 2
RETRY_BASE_DELAY = 1.0  # seconds

# Rate limit error detection
RATE_LIMIT_ERRORS = [
    "429",
    "rate limit",
    "RESOURCE_EXHAUSTED",
    "quota exceeded",
    "too many requests"
]

# Temporary errors that should be retried
RETRIABLE_ERRORS = [
    "500",
    "502",
    "503",
    "504",
    "timeout",
    "timed out",
    "connection",
    "network"
]

# Input sanitization configuration
MAX_INPUT_LENGTH = 5000  # Maximum characters for user input

# Prompt injection patterns to detect and neutralize
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"ignore\s+(all\s+)?rules?",
    r"forget\s+everything",
    r"forget\s+(all\s+)?(your\s+)?(instructions?|rules?|system)?",
    r"you\s+are\s+now\s+",
    r"you\s+are\s+a\s+",
    r"act\s+as\s+",
    r"pretend\s+(to\s+be|you\s+are)",
    r"system\s+prompt",
    r"#system",
    r"override\s+(your\s+)?",
    r"jailbreak",
    r" DAN ",  # "Do Anything Now"
    r"developer\s+mode",
    r"\{\{.*\}\}",  # Template injection
    r"<\?xml",  # XML injection
    r"<!\[CDATA\[",
    r"```system",
    r"#@\s*system",
    r"\\[SYSTEM\\]",
    r"\[INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
    r"###\s*Instructions",
    r"Role:",
    r"New\s+instruction",
    r"Additional\s+instruction",
    r"disregard\s+(your\s+)?",
    r"disobey\s+",
    r"without\s+your\s+(filters?|rules?|guidelines?)",
    r"bypass\s+",
]

# Compile patterns for efficiency
_COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def sanitize_user_input(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """
    Sanitize user-provided text before inserting into Gemini prompts.
    
    This function:
    - Trims text to maximum length
    - Detects and neutralizes prompt injection patterns
    - Logs warnings when potential injection is detected
    
    Returns the sanitized text.
    """
    if not text:
        return text
    
    original_length = len(text)
    
    # Step 1: Check for potential injection patterns
    injection_detected = False
    for pattern in _COMPILED_INJECTION_PATTERNS:
        if pattern.search(text):
            injection_detected = True
            # Replace the matched pattern with a safe placeholder
            text = pattern.sub("[FILTERED]", text)
    
    if injection_detected:
        import logging
        logging.warning(
            f"Potential prompt injection detected and neutralized. "
            f"Original length: {original_length}, Sanitized length: {len(text)}"
        )
    
    # Step 2: Trim to max length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env file")

client_genai = genai.Client(api_key=GEMINI_API_KEY)

# Cache configuration
CACHE_MAX_SIZE = 100  # Maximum number of entries
CACHE_TTL_SECONDS = 3600  # 1 hour TTL

# Cache state with TTL tracking
# Using OrderedDict for LRU behavior: most recently used stays at end
_analysis_cache = OrderedDict()  # {cache_key: (timestamp, data)}
_cache_timestamps = {}  # {cache_key: timestamp}
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


def _cleanup_cache():
    """
    Remove expired entries and enforce max size limit.
    Uses LRU: removes oldest entries when at capacity.
    """
    global _analysis_cache, _cache_timestamps
    current_time = time.time()
    
    # Remove expired entries
    expired_keys = [
        key for key, ts in _cache_timestamps.items()
        if current_time - ts > CACHE_TTL_SECONDS
    ]
    for key in expired_keys:
        _analysis_cache.pop(key, None)
        _cache_timestamps.pop(key, None)
    
    # Enforce max size (LRU: remove oldest entries)
    while len(_analysis_cache) > CACHE_MAX_SIZE:
        oldest_key = next(iter(_analysis_cache))
        _analysis_cache.pop(oldest_key)
        _cache_timestamps.pop(oldest_key, None)


def _is_rate_limit_error(error: Exception) -> bool:
    """Check if error is a rate limit error."""
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in RATE_LIMIT_ERRORS)


def _is_retriable_error(error: Exception) -> bool:
    """Check if error is a temporary error that should be retried."""
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in RETRIABLE_ERRORS)


def _generate_with_retry(prompt: str) -> str:
    """
    Generate content with retry logic.
    - Does NOT retry on rate limit errors (429)
    - Retries with exponential backoff on temporary errors (max 2 retries)
    """
    last_exception = None
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client_genai.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            last_exception = e
            
            # If it's a rate limit error, do NOT retry - return immediately
            if _is_rate_limit_error(e):
                raise RateLimitError(
                    "Gemini API rate limit exceeded. Please wait a moment and try again."
                ) from e
            
            # If it's a retriable error and we have retries left
            if attempt < MAX_RETRIES and _is_retriable_error(e):
                delay = RETRY_BASE_DELAY * (2 ** attempt)  # Exponential backoff
                print(f"Retryable error on attempt {attempt + 1}, waiting {delay}s: {str(e)}")
                time.sleep(delay)
                continue
            
            # For non-retriable errors or max retries reached, raise
            raise
    
    raise last_exception


class RateLimitError(Exception):
    """Custom exception for rate limit errors."""
    pass


def _generate(prompt: str) -> str:
    return _generate_with_retry(prompt)


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

    # Sanitize all user-provided inputs
    # Create sanitized copy of user_profile
    sanitized_profile = {}
    if user_profile:
        for key, value in user_profile.items():
            if isinstance(value, str):
                sanitized_profile[key] = sanitize_user_input(value)
            elif isinstance(value, list):
                sanitized_profile[key] = [
                    sanitize_user_input(str(item)) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized_profile[key] = value
    
    # Sanitize resume text (limit to 3000 chars after sanitization)
    sanitized_resume = sanitize_user_input(resume_text, max_length=3000)
    
    # Sanitize GitHub and LeetCode data (convert to string and sanitize)
    sanitized_github = sanitize_user_input(json.dumps(github_data or {}), max_length=MAX_INPUT_LENGTH)
    sanitized_leetcode = sanitize_user_input(json.dumps(leetcode_data or {}), max_length=MAX_INPUT_LENGTH)

    prompt = f"""
You are an expert AI Career Mentor. Analyze this candidate 
profile completely and provide personalized career guidance.

===== USER PROFILE =====
User Type: {sanitized_profile.get('user_type', 'Not specified')}

--- Education ---
College: {sanitized_profile.get('college_name', 'Not specified')}
Degree: {sanitized_profile.get('degree', 'Not specified')}
Branch: {sanitized_profile.get('branch', 'Not specified')}
Year of Study: {sanitized_profile.get('year_of_study', 'Not specified')}
Graduation Year: {sanitized_profile.get('graduation_year', 'Not specified')}
CGPA: {sanitized_profile.get('cgpa', 'Not specified')}

--- Professional ---
Current Job Title: {sanitized_profile.get('current_job_title', 'Not specified')}
Current Company: {sanitized_profile.get('current_company', 'Not specified')}
Years of Experience: {sanitized_profile.get('years_of_experience', 'Not specified')}
Current Tech Stack: {sanitized_profile.get('current_tech_stack', [])}
Reason for Switching: {sanitized_profile.get('reason_for_switching', 'Not specified')}

--- Career Goals ---
Career Goal: {sanitized_profile.get('career_goal', 'Not specified')}
Target Companies: {sanitized_profile.get('target_companies', [])}
Preferred Work Type: {sanitized_profile.get('preferred_work_type', 'Not specified')}
Job Search Timeline: {sanitized_profile.get('job_search_timeline', 'Not specified')}

--- Skills ---
Extra Skills: {sanitized_profile.get('extra_skills', [])}
Certificates: {sanitized_profile.get('certificates', [])}

===== GITHUB DATA =====
{sanitized_github}

===== LEETCODE DATA =====
{sanitized_leetcode}

===== RESUME =====
{sanitized_resume[:3000] if sanitized_resume else "Not provided"}

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
    }},
    "path_details": {{
        "Career Path 1 Name": {{
            "skill_gaps": [
                {{
                    "skill": "Skill Name",
                    "have": false,
                    "priority": 1,
                    "resources": ["Resource 1", "Resource 2"]
                }}
            ],
            "roadmap": {{
                "target_career": "Career Path 1 Name",
                "duration_months": 6,
                "total_weeks": 24,
                "milestones": [
                    {{
                        "week": 1,
                        "title": "Milestone Title",
                        "description": "What to accomplish",
                        "skills": ["skill1", "skill2"],
                        "deliverable": "What to build"
                    }}
                ]
            }}
        }},
        "Career Path 2 Name": {{
            "skill_gaps": [],
            "roadmap": {{}}
        }},
        "Career Path 3 Name": {{
            "skill_gaps": [],
            "roadmap": {{}}
        }}
    }}
}}

For each of the 3 career paths in career_paths, generate a SEPARATE and SPECIFIC 
skill_gaps list and roadmap tailored to that exact career path. Store these in 
path_details using the career path name as the key. Each path must have its own 
unique skill_gaps and roadmap — do NOT reuse the same content across paths.
"""
    MAX_JSON_RETRIES = 2
    for json_attempt in range(MAX_JSON_RETRIES + 1):
        try:
            raw_text = _generate(prompt)
            clean_text = _clean_json(raw_text)
            result = json.loads(clean_text)
            return {"success": True, "data": result}
        except RateLimitError as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "rate_limit",
                "retry_after": None
            }
        except json.JSONDecodeError as e:
            if json_attempt < MAX_JSON_RETRIES:
                print(f"JSON parse failed on attempt {json_attempt + 1}, retrying Gemini call: {str(e)}")
                time.sleep(1.0)
                continue
            return {
                "success": False,
                "error": f"Failed to parse AI response after {MAX_JSON_RETRIES + 1} attempts: {str(e)}"
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
    global _last_github_data, _last_leetcode_data, _analysis_cache, _cache_timestamps
    
    # Store the most recent inputs
    if github_data: _last_github_data = github_data
    if leetcode_data: _last_leetcode_data = leetcode_data
    
    # Clean up expired entries and enforce size limit
    _cleanup_cache()
    
    cache_key = str(github_data) + str(leetcode_data) + str(resume_text[:100]) + str(user_profile)
    current_time = time.time()
    
    # Check if valid cache entry exists
    if cache_key in _analysis_cache:
        # Check if not expired
        if cache_key in _cache_timestamps:
            if current_time - _cache_timestamps[cache_key] <= CACHE_TTL_SECONDS:
                # Move to end (most recently used) for LRU
                _analysis_cache.move_to_end(cache_key)
                return _analysis_cache[cache_key], None
            else:
                # Expired - remove it
                _analysis_cache.pop(cache_key, None)
                _cache_timestamps.pop(cache_key, None)
    
    # Cache miss - run analysis
    result = run_combined_analysis(
        github_data,
        leetcode_data,
        resume_text,
        user_profile
    )
    if result["success"]:
        # Clean up before adding new entry
        _cleanup_cache()
        # Add to cache with timestamp
        _analysis_cache[cache_key] = result["data"]
        _cache_timestamps[cache_key] = current_time
        # Move to end for LRU
        _analysis_cache.move_to_end(cache_key)
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

    # Sanitize user-provided inputs
    sanitized_career_path = sanitize_user_input(career_path)
    sanitized_difficulty = sanitize_user_input(difficulty)
    sanitized_resume = sanitize_user_input(resume_text, max_length=500)
    
    # Sanitize profile dict values
    sanitized_profile = {}
    if profile:
        for key, value in profile.items():
            if isinstance(value, str):
                sanitized_profile[key] = sanitize_user_input(value)
            elif isinstance(value, list):
                sanitized_profile[key] = [
                    sanitize_user_input(str(item)) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized_profile[key] = value

    prompt = f"""You are an expert technical interviewer.
{personality_instruction}

Session ID: {random.randint(10000, 99999)}
Timestamp: {int(time.time())}
Generate FRESH unique questions - do not repeat previous sessions.

Generate exactly 5 interview questions for: {sanitized_career_path}
Difficulty: {sanitized_difficulty}
Profile: {json.dumps(sanitized_profile)}
{f"Resume highlights: {sanitized_resume[:500]}" if sanitized_resume else ""}

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
    except RateLimitError as e:
        print(f"Rate limit error in interview questions: {str(e)}")
        return []
    except json.JSONDecodeError as e:
        print(f"Failed to parse interview questions: {str(e)}")
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
        except RateLimitError as e:
            print(f"Rate limit error on retry: {str(e)}")
            return []
        except Exception as e2:
            print(f"Gemini attempt 2 also failed: {str(e2)}")
            return []


def evaluate_interview_answer(
    question: str,
    answer: str,
    career_path: str
) -> dict:
    # Sanitize all user inputs
    sanitized_question = sanitize_user_input(question)
    sanitized_answer = sanitize_user_input(answer, max_length=2000)
    sanitized_career_path = sanitize_user_input(career_path)
    
    prompt = f"""You are an expert technical interviewer for {sanitized_career_path}.

Question: {sanitized_question}
Candidate Answer: {sanitized_answer}

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
