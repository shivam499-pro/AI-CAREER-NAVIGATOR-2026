from dotenv import load_dotenv
import os

# Load environment variables FIRST — before any local imports
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import analysis, jobs, auth, resume, profile_enhanced, interview, streaks, ranks, challenges, weekly_challenge, badges, email_report, documents

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
app.include_router(weekly_challenge.router, prefix="/api/weekly", tags=["Weekly Challenge"])
app.include_router(badges.router, prefix="/api/badges", tags=["Badges"])
app.include_router(email_report.router, prefix="/api/email", tags=["Email Report"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Career Navigator API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
