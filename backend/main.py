from dotenv import load_dotenv
import os

# Load environment variables FIRST — before any local imports
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import profile, analysis, jobs, auth, resume, profile_enhanced, interview

# Create FastAPI app
app = FastAPI(
    title="AI Career Navigator API",
    description="Backend API for AI Career Navigator - Your personal AI-powered career mentor",
    version="1.0.0"
)

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
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(profile_enhanced.router, prefix="/api/profile", tags=["Profile Enhanced"])
app.include_router(interview.router, prefix="/api/interview", tags=["Interview"])

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
