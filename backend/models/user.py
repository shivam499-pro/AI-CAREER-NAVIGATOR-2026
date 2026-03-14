"""
User Data Models
Pydantic models for user-related data
"""
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserProfile(BaseModel):
    """User profile model."""
    id: str
    email: EmailStr
    created_at: datetime
    github_url: Optional[str] = None
    leetcode_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    resume_url: Optional[str] = None
    analysis_complete: bool = False
    
    class Config:
        from_attributes = True

class ProfileInput(BaseModel):
    """Profile input model for submissions."""
    github_url: Optional[str] = None
    leetcode_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    def validate_github_url(self) -> bool:
        """Validate GitHub URL format."""
        if self.github_url:
            return "github.com" in self.github_url
        return True
    
    def validate_linkedin_url(self) -> bool:
        """Validate LinkedIn URL format."""
        if self.linkedin_url:
            return "linkedin.com" in self.linkedin_url
        return True
