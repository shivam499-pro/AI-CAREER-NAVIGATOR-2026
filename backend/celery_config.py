"""
Celery Configuration
Distributed task queue setup for background job processing.
"""
import os
import logging
from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# Celery configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "career_navigator",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "services.async_job_service",
        "services.analysis_service",
        "services.resume_service",
    ]
)

# Celery configuration options
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Result backend settings
    result_expires=86400,  # 24 hours
    result_extended=True,
    
    # Task routing
    task_routes={
        "services.async_job_service.process_analysis_job": {"queue": "analysis"},
        "services.resume_service.process_resume": {"queue": "resume"},
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-jobs": {
            "task": "services.async_job_service.cleanup_old_jobs",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        },
        "update-market-data": {
            "task": "services.market_analyzer.update_market_data",
            "schedule": crontab(hour="*/6"),  # Every 6 hours
        },
    },
)


# Task base class with error handling
class TaskWithRetry(celery_app.Task):
    """Base task class with automatic retry and error handling."""
    
    autoretry_for = (Exception,)
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Task {task_id} failed: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(f"Task {task_id} retrying: {exc}")
        super().on_retry(exc, task_id, args, kwargs, einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Task {task_id} succeeded")
        super().on_success(retval, task_id, args, kwargs)


# Health check task
@celery_app.task(bind=True, base=TaskWithRetry)
def health_check_task(self):
    """Health check task to verify worker is running."""
    return {"status": "healthy", "worker": self.request.hostname}


# Cleanup old jobs task
@celery_app.task
def cleanup_old_jobs():
    """Clean up old completed/failed jobs from database."""
    from datetime import datetime, timedelta, timezone
    from services.async_job_service import async_job_service
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        # This would clean up old jobs in the database
        logger.info(f"Cleaning up jobs older than {cutoff_date}")
        
        return {"cleaned": 0}
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"error": str(e)}


# Run worker command:
# celery -A backend.celery_config worker --loglevel=info -Q analysis,resume
#
# Run beat command:
# celery -A backend.celery_config beat --loglevel=info
