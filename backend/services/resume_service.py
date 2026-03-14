"""
Resume PDF Parser Service
Extracts text from uploaded PDF resumes using PyMuPDF
"""
import fitz  # PyMuPDF

def extract_text(file_path: str) -> str:
    """
    Extract text from a PDF file.
    """
    doc = fitz.open(file_path)
    text = ""
    
    for page in doc:
        text += page.get_text()
    
    doc.close()
    return text

def extract_skills(text: str) -> list:
    """
    Extract potential skills from resume text.
    """
    # Common programming languages
    languages = [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go",
        "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R"
    ]
    
    # Common frameworks
    frameworks = [
        "React", "Angular", "Vue", "Node.js", "Django", "Flask",
        "FastAPI", "Spring", "Express", "Next.js", "Tailwind"
    ]
    
    # Common tools
    tools = [
        "Git", "Docker", "Kubernetes", "AWS", "GCP", "Azure",
        "PostgreSQL", "MongoDB", "Redis", "Linux", "SQL"
    ]
    
    found_skills = []
    text_lower = text.lower()
    
    for skill in languages + frameworks + tools:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    
    return found_skills

def extract_experience(text: str) -> list:
    """
    Extract work experience from resume text.
    """
    # Simple extraction - looks for common patterns
    # In production, would use more sophisticated NLP
    experiences = []
    
    # Look for job titles
    job_keywords = ["Engineer", "Developer", "Manager", "Analyst", "Designer"]
    
    for keyword in job_keywords:
        if keyword.lower() in text.lower():
            experiences.append(keyword)
    
    return experiences
