from dotenv import load_dotenv
import os
import sys
from datetime import datetime

# Load environment variables FIRST — before any local imports
load_dotenv()


def validate_environment():
    """
    Validate that all required environment variables are present.
    Exits with error code if any required variable is missing.
    """
    required_vars = {
        # Supabase (required for all database operations)
        "SUPABASE_URL": "Supabase project URL",
        "SUPABASE_SERVICE_KEY": "Supabase service role key (backend only)",
        
        # Gemini AI (required for analysis and interview features)
        "GEMINI_API_KEY": "Google Gemini API key for AI features",
    }
    
    optional_vars = {
        # Supabase
        "SUPABASE_ANON_KEY": "Supabase anon key (frontend)",
        
        # External APIs
        "GITHUB_TOKEN": "GitHub personal access token (for higher rate limits)",
        "SERPAPI_KEY": "SerpAPI key for job search",
        
        # Email
        "GMAIL_USER": "Gmail address for weekly reports",
        "GMAIL_APP_PASSWORD": "Gmail app password for sending emails",
        
        # Server config
        "CORS_ORIGINS": "Comma-separated list of allowed CORS origins",
    }
    
    missing_required = []
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value or value.strip() == "":
            missing_required.append(f"  - {var_name}: {description}")
    
    if missing_required:
        print("\n" + "=" * 60)
        print("ERROR: Missing required environment variables")
        print("=" * 60)
        print("\nThe following required variables are missing or empty:\n")
        print("\n".join(missing_required))
        print("\n" + "-" * 60)
        print("To fix this, copy .env.example to .env and fill in the values.")
        print("=" * 60 + "\n")
        sys.exit(1)
    
    # Warn about missing optional but commonly needed vars
    missing_optional = []
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if not value or value.strip() == "":
            missing_optional.append(f"  - {var_name}: {description}")
    
    
    if missing_optional:
        print("\n[INFO] Optional environment variables not set:")
        print("\n".join(missing_optional))
        print("\n[INFO] Some features may not work without these.")
    
    print("\n[OK] Environment validation passed!")


# Validate environment before starting the app
validate_environment()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import analysis, jobs, auth, resume, profile_enhanced, interview, streaks, ranks, challenges, weekly_challenge, badges, email_report, documents, career

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create FastAPI app
app = FastAPI(
    title="AI Career Navigator API",
    description="Backend API for AI Career Navigator - Your personal AI-powered career mentor",
    version="1.0.0"
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(profile_enhanced.router, prefix="/api/profile", tags=["Profile Enhanced"])
app.include_router(interview.router, prefix="/api/interview", tags=["Interview"])
app.include_router(streaks.router, prefix="/api/streaks", tags=["Streaks"])
app.include_router(ranks.router, prefix="/api/ranks", tags=["Ranks"])
app.include_router(challenges.router, prefix="/api/challenges", tags=["Challenges"])
app.include_router(weekly_challenge.router, prefix="/api/weekly-challenge", tags=["Weekly Challenge"])
app.include_router(badges.router, prefix="/api/badges", tags=["Badges"])
app.include_router(email_report.router, prefix="/api/email", tags=["Email Report"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(career.router, prefix="/api/career", tags=["Career Evolution"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Career Navigator API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """
    Enhanced health check with service status.
    Returns 200 OK even if services are down.
    """
    # Check database (Supabase)
    db_ok = False
    try:
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        if supabase_url and supabase_key:
            supabase = create_client(supabase_url, supabase_key)
            # Simple health check - just verify we can create client
            db_ok = True
    except:
        pass
    
    # Check Gemini
    gemini_ok = False
    try:
        import google.genai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            gemini_ok = True
    except:
        pass
    
    # Memory engine always OK if backend is running
    memory_ok = True
    
    services = {
        "database": db_ok,
        "gemini": gemini_ok,
        "memory_engine": memory_ok
    }
    
    return {
        "status": "healthy",
        "services": services
    }


# Global Error Handler Middleware
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Catch ALL unhandled exceptions and return safe JSON.
    Never leak stack traces to frontend.
    """
    from fastapi.responses import JSONResponse
    
    # Log the actual error server-side
    logger.error(
        f"[BACKEND][GLOBAL] action=unhandled_exception "
        f"path={request.url.path} error={str(exc)}"
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": "Internal server error",
            "source": "global_error_handler",
            "meta": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "execution_time_ms": 0
            }
        }
    )

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
