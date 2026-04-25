"""
Core Configuration
Loads and provides access to environment variables and app settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    
    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # GitHub
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    
    # SerpAPI
    SERPAPI_KEY: Optional[str] = os.getenv("SERPAPI_KEY")
    
    # Email
    GMAIL_USER: Optional[str] = os.getenv("GMAIL_USER")
    GMAIL_APP_PASSWORD: Optional[str] = os.getenv("GMAIL_APP_PASSWORD")
    
    # Server
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # API
    API_V1_PREFIX: str = "/api"
    
    @classmethod
    def get_supabase_url(cls) -> str:
        """Get Supabase URL."""
        return cls.SUPABASE_URL
    
    @classmethod
    def get_service_key(cls) -> str:
        """Get Supabase service role key."""
        return cls.SUPABASE_SERVICE_KEY
    
    @classmethod
    def get_anon_key(cls) -> str:
        """Get Supabase anon key."""
        return cls.SUPABASE_ANON_KEY
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production."""
        return os.getenv("ENV", "development") == "production"


# Create singleton instance
settings = Settings()