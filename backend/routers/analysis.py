"""
Analysis Router
Unified analysis API endpoints.

POST /api/analysis/run - Run AI analysis (async with job tracking)
GET /api/analysis/job/{job_id} - Get job status
GET /api/analysis/jobs - Get user's job history
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services import analysis_service
from services.async_job_service import (
    create_analysis_job_idempotent,
    get_job_status,
    get_user_job_history,
    async_job_service
)

# Import security middleware components
from core.middleware import (
    get_current_user,
    AuthenticatedUser,
    APIResponse,
    require_permission,
    Permission
)

router = APIRouter()


# Background task function
async def process_analysis_background(job_id: str, payload: dict):
    """Background task to process analysis job."""
    await async_job_service.process_analysis_job(job_id, payload)


# Using centralized get_current_user from middleware


@router.get("/")
async def get_my_analysis(user: AuthenticatedUser = Depends(get_current_user)):
    """
    Get current user's analysis.
    """
    try:
        analysis = analysis_service.get_analysis_by_user_id(user.user_id)
        
        if not analysis:
            return APIResponse.success_response(
                data={
                    "exists": False,
                    "analysis": None
                }
            )
        
        return APIResponse.success_response(
            data={
                "exists": True,
                "analysis": analysis
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="ANALYSIS_FETCH_ERROR"
            )
        )


@router.post("/run")
async def run_my_analysis(
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user)
    ):
    """
    Run AI analysis for current user (async with background processing).
    
    Creates a job and returns immediately while analysis runs in background.
    Use /api/analysis/job/{job_id} to check status.
    """
    try:
        # Create async job (idempotent to prevent duplicates)
        job, is_new = await create_analysis_job_idempotent(user.user_id, duplicate_window_seconds=300)
        
        # Only process if this is a new job, not a duplicate
        if is_new:
            background_tasks.add_task(
                process_analysis_background,
                job_id=job["id"],
                payload=job["payload"]
            )
        
        return APIResponse.success_response(
            data={
                "job_id": job["id"],
                "status": job["status"],
                "message": "Analysis started in background"
            },
            message="Analysis job created"
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="ANALYSIS_JOB_ERROR"
            )
        )


@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get status of an analysis job.
    """
    try:
        job = await get_job_status(job_id)
        
        if not job:
            return JSONResponse(
                status_code=404,
                content=APIResponse.error_response(
                    "Job not found",
                    code="JOB_NOT_FOUND"
                )
            )
        
        # Verify user owns this job
        if job.get("user_id") != user.user_id:
            return JSONResponse(
                status_code=403,
                content=APIResponse.error_response(
                    "Access denied",
                    code="ACCESS_DENIED"
                )
            )
        
        return APIResponse.success_response(
            data=job
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="JOB_STATUS_ERROR"
            )
        )


@router.get("/jobs")
async def get_analysis_jobs(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get user's analysis job history.
    """
    try:
        jobs = await get_user_job_history(user.user_id)
        return APIResponse.success_response(
            data={"jobs": jobs}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="JOBS_LIST_ERROR"
            )
        )


@router.get("/career-paths")
async def get_career_paths(user: AuthenticatedUser = Depends(get_current_user)):
    """
    Get career path recommendations.
    """
    try:
        recommendations = analysis_service.get_career_recommendations(user.user_id)
        return APIResponse.success_response(
            data={"career_paths": recommendations}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="CAREER_PATHS_ERROR"
            )
        )


@router.get("/skill-gap")
async def get_skill_gaps(user: AuthenticatedUser = Depends(get_current_user)):
    """
    Get skill gaps.
    """
    try:
        gaps = analysis_service.get_skill_gaps(user.user_id)
        return APIResponse.success_response(
            data={"skill_gaps": gaps}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error_response(
                str(e),
                code="SKILL_GAP_ERROR"
            )
        )
