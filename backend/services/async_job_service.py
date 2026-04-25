"""
Async Job Service
Background job processing for long-running tasks like AI analysis.
Includes idempotency support to prevent duplicate jobs.
"""
import logging
import os
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional
from enum import Enum

from supabase import create_client

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    """Job type enum."""
    ANALYSIS = "analysis"
    DOCUMENT_PROCESSING = "document_processing"
    JOB_RECOMMENDATIONS = "job_recommendations"


class AsyncJobService:
    """
    Service for managing async background jobs.
    Uses Supabase as the backing store for job state.
    """
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        self._supabase = create_client(supabase_url, supabase_key)
    
    def _generate_idempotency_key(self, job_type: JobType, user_id: str, payload: dict) -> str:
        """
        Generate an idempotency key for a job.
        
        The key is based on job_type, user_id, and a hash of the payload.
        This ensures the same job won't be created twice within the duplicate window.
        """
        payload_str = str(sorted(payload.items()))
        payload_hash = hashlib.md5(payload_str.encode()).hexdigest()[:8]
        return f"{job_type.value}:{user_id}:{payload_hash}"
    
    async def ensure_single_job(
        self,
        job_type: JobType,
        user_id: str,
        payload: dict,
        duplicate_window_seconds: int = 300
    ) -> tuple[Optional[dict], bool]:
        """
        Ensure only a single job exists for the given parameters.
        
        If a job of the same type for the same user exists within the duplicate window,
        return the existing job instead of creating a new one.
        
        Args:
            job_type: Type of job to create
            user_id: User ID
            payload: Job payload
            duplicate_window_seconds: Time window to consider as duplicate (default 5 minutes)
        
        Returns:
            tuple of (job dict or None, is_new bool)
            - If is_new=True, a new job was created
            - If is_new=False, an existing job was returned
        """
        idempotency_key = self._generate_idempotency_key(job_type, user_id, payload)
        
        # Calculate the cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=duplicate_window_seconds)
        
        # Check for existing pending/processing jobs
        response = (
            self._supabase.table("analysis_jobs")
            .select("*")
            .eq("job_type", job_type.value)
            .eq("user_id", user_id)
            .in_("status", [JobStatus.PENDING.value, JobStatus.PROCESSING.value])
            .gte("created_at", cutoff_time.isoformat())
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            # Return existing job instead of creating a new one
            logger.info(f"Found existing job for {idempotency_key}, returning existing")
            return response.data[0], False
        
        # No duplicate found, create new job
        job = await self.create_job(job_type, user_id, payload)
        return job, True
    
    async def create_job(
        self,
        job_type: JobType,
        user_id: str,
        payload: dict
    ) -> dict:
        """Create a new async job."""
        job_data = {
            "job_type": job_type.value,
            "user_id": user_id,
            "status": JobStatus.PENDING.value,
            "payload": payload,
            "result": None,
            "error_message": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        response = self._supabase.table("analysis_jobs").insert(job_data).execute()
        
        if response.data:
            return response.data[0]
        
        raise Exception("Failed to create job")
    
    async def get_job(self, job_id: str) -> Optional[dict]:
        """Get job by ID."""
        response = self._supabase.table("analysis_jobs").select("*").eq("id", job_id).execute()
        
        if response.data:
            return response.data[0]
        
        return None
    
    async def get_user_jobs(self, user_id: str, limit: int = 10) -> list:
        """Get jobs for a user."""
        response = (
            self._supabase.table("analysis_jobs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        return response.data or []
    
    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Optional[dict] = None,
        error_message: Optional[str] = None
    ):
        """Update job status."""
        update_data = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if result is not None:
            update_data["result"] = result
        
        if error_message is not None:
            update_data["error_message"] = error_message
        
        self._supabase.table("analysis_jobs").update(update_data).eq("id", job_id).execute()
    
    async def mark_processing(self, job_id: str):
        """Mark job as processing."""
        await self.update_job_status(job_id, JobStatus.PROCESSING)
    
    async def mark_completed(self, job_id: str, result: dict):
        """Mark job as completed."""
        await self.update_job_status(job_id, JobStatus.COMPLETED, result=result)
    
    async def mark_failed(self, job_id: str, error: str):
        """Mark job as failed."""
        await self.update_job_status(job_id, JobStatus.FAILED, error_message=error)
    
    async def process_analysis_job(self, job_id: str, payload: dict):
        """
        Process an analysis job.
        This is called by the background task runner.
        """
        from services import analysis_service
        
        user_id = payload.get("user_id")
        
        try:
            # Mark as processing
            await self.mark_processing(job_id)
            
            # Run the analysis
            result = await analysis_service.run_analysis(user_id)
            
            # Mark as completed with result
            await self.mark_completed(job_id, result)
            
            logger.info(f"Analysis job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Analysis job {job_id} failed: {e}")
            await self.mark_failed(job_id, str(e))


# Global instance
async_job_service = AsyncJobService()


async def create_analysis_job(user_id: str) -> dict:
    """Create an async analysis job and return immediately."""
    return await async_job_service.create_job(
        job_type=JobType.ANALYSIS,
        user_id=user_id,
        payload={"user_id": user_id}
    )


async def create_analysis_job_idempotent(user_id: str, duplicate_window_seconds: int = 300) -> tuple[dict, bool]:
    """
    Create an async analysis job with idempotency.
    
    Prevents duplicate jobs from being created within the duplicate window.
    
    Returns:
        tuple of (job dict, is_new bool)
    """
    return await async_job_service.ensure_single_job(
        job_type=JobType.ANALYSIS,
        user_id=user_id,
        payload={"user_id": user_id},
        duplicate_window_seconds=duplicate_window_seconds
    )


async def get_job_status(job_id: str) -> Optional[dict]:
    """Get job status."""
    return await async_job_service.get_job(job_id)


async def get_user_job_history(user_id: str, limit: int = 10) -> list:
    """Get user's job history."""
    return await async_job_service.get_user_jobs(user_id, limit)