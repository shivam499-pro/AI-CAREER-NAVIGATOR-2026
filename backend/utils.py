"""
Backend Utilities
Production-grade utilities for fault-tolerant API responses.
"""
from typing import Any, Optional, Dict
from datetime import datetime
import time
import logging
import functools

logger = logging.getLogger(__name__)

# Backend log prefix
BACKEND_LOG_PREFIX = "[BACKEND]"


def create_response(
    data: Any = None,
    success: bool = True,
    error: Optional[str] = None,
    source: str = "db"
) -> Dict[str, Any]:
    """
    Create standardized API response.
    
    Args:
        data: Response data payload
        success: Whether request succeeded
        error: Error message if failure
        source: Data source (cache|db|fallback|error_handler)
    
    Returns:
        Standardized response dict
    """
    return {
        "success": success,
        "data": data,
        "error": error,
        "source": source,
        "meta": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "execution_time_ms": 0  # Will be updated by wrapper
        }
    }


def with_timing(fn):
    """Decorator to add execution timing to responses."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = fn(*args, **kwargs)
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Add timing to response if it's a dict
        if isinstance(result, dict) and "meta" in result:
            result["meta"]["execution_time_ms"] = elapsed_ms
        
        return result
    return wrapper


def logStructured(
    module: str,
    action: str,
    user_id: Optional[str] = None,
    status: str = "success",
    latency_ms: int = 0
) -> None:
    """
    Structured logging for backend actions.
    
    Format: [BACKEND][MODULE] action=... user_id=... status=... latency_ms=...
    """
    parts = [
        f"{BACKEND_LOG_PREFIX}[{module}]",
        f"action={action}",
    ]
    
    if user_id:
        parts.append(f"user_id={user_id}")
    
    parts.extend([
        f"status={status}",
        f"latency_ms={latency_ms}"
    ])
    
    log_message = " ".join(parts)
    
    if status == "error":
        logger.error(log_message)
    else:
        logger.info(log_message)


def safe_timeout(seconds: int = 5):
    """
    Decorator to add timeout protection to functions.
    
    Note: This is a placeholder. For actual timeout,
    use signal or async approaches in FastAPI.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def handle_service_error(
    module: str,
    action: str,
    fallback_data: Any = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create error response with logging.
    
    Args:
        module: Module name (INTERVIEW, MEMORY, etc.)
        action: Action that failed
        fallback_data: Safe fallback data
        user_id: User context
    
    Returns:
        Standardized error response with fallback
    """
    logStructured(module, action, user_id, "error", 0)
    
    return create_response(
        data=fallback_data,
        success=False,
        error=f"Service temporarily unavailable",
        source="error_handler"
    )