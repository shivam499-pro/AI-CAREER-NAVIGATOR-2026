"""
Google Gemini AI Service
Handles all AI-powered analysis and generation using Gemini API
"""
import os
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

GEMINI_MODEL = "gemini-1.5-flash"

def analyze_profile(profile_data: dict) -> dict:
    """
    Analyze all profile data and generate comprehensive analysis.
    """
    prompt = f"""
    Analyze the following profile data and provide career recommendations:
    
    Profile Data: {profile_data}
    
    Please provide a JSON response with:
    1. Key strengths (array of strings)
    2. Areas for improvement (array of strings)
    3. Experience level assessment: "Beginner", "Intermediate", or "Advanced"
    4. Top 3 career path recommendations with match percentages and reasoning
    5. Skill gap analysis
    
    Format the response as valid JSON.
    """
    
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    
    return {"analysis": response.text}

def generate_career_paths(analysis: dict) -> list:
    """
    Generate career path recommendations based on analysis.
    """
    prompt = f"""
    Based on the following analysis, recommend the top 3-5 career paths.
    
    Analysis: {analysis}
    
    Provide a JSON array of career paths with:
    - name: Career name
    - match_percentage: 0-100
    - reason: Reasoning based on their skills
    
    Return ONLY valid JSON array.
    """
    
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    
    return {"paths": response.text}

def generate_skill_gaps(analysis: dict, target_career: str) -> list:
    """
    Generate skill gap analysis for a target career.
    """
    prompt = f"""
    Based on the analysis and target career of {target_career}, provide a skill gap analysis.
    
    Analysis: {analysis}
    Target Career: {target_career}
    
    Provide a JSON array of skills with:
    - skill: Skill name
    - have: true if user has it, false if missing
    - priority: 1-5 (1 is highest priority)
    - resources: Array of suggested learning resources
    
    Return ONLY valid JSON array.
    """
    
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    
    return {"skill_gaps": response.text}

def generate_roadmap(analysis: dict, target_career: str) -> dict:
    """
    Generate a personalized career roadmap.
    """
    prompt = f"""
    Create a detailed career roadmap for becoming a {target_career}.
    
    User Analysis: {analysis}
    
    Include:
    1. Duration in months
    2. Weekly milestones with:
       - week number
       - title
       - description
       - skills to learn
       - completed: false
    
    Provide a JSON object with:
    - target_career: string
    - duration_months: number
    - milestones: array of milestone objects
    
    Return ONLY valid JSON.
    """
    
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    
    return {"roadmap": response.text}
