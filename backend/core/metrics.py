"""
Metrics Middleware
Provides request counters, error counters, and slow request logging.
"""
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and provides metrics for the application.
    Tracks request counts, error counts, and slow requests.
    """
    
    def __init__(self, max_history: int = 1000):
        self._max_history = max_history
        
        # Counters
        self._request_count: int = 0
        self._error_count: int = 0
        self._slow_request_count: int = 0
        
        # By endpoint
        self._endpoint_counts: Dict[str, int] = defaultdict(int)
        self._endpoint_errors: Dict[str, int] = defaultdict(int)
        self._endpoint_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Slow request threshold (ms)
        self._slow_threshold_ms: float = 3000
        
        # Recent slow requests (last 50)
        self._slow_requests = deque(maxlen=50)
    
    def record_request(self, endpoint: str, duration_ms: float, status_code: int):
        """Record a request."""
        self._request_count += 1
        self._endpoint_counts[endpoint] += 1
        
        # Record timing
        self._endpoint_times[endpoint].append(duration_ms)
        
        # Check for errors (4xx/5xx)
        if status_code >= 400:
            self._error_count += 1
            self._endpoint_errors[endpoint] += 1
        
        # Check for slow requests
        if duration_ms > self._slow_threshold_ms:
            self._slow_request_count += 1
            self._slow_requests.append({
                "endpoint": endpoint,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
    
    def get_stats(self) -> dict:
        """Get current metrics stats."""
        # Calculate avg response times per endpoint
        endpoint_avgs = {}
        for endpoint, times in self._endpoint_times.items():
            if times:
                endpoint_avgs[endpoint] = round(sum(times) / len(times), 2)
        
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "slow_requests": self._slow_request_count,
            "error_rate": round(self._error_count / max(self._request_count, 1) * 100, 2),
            "by_endpoint": dict(self._endpoint_counts),
            "errors_by_endpoint": dict(self._endpoint_errors),
            "avg_response_time_ms": endpoint_avgs,
            "slow_threshold_ms": self._slow_threshold_ms,
            "recent_slow_requests": list(self._slow_requests)
        }
    
    def reset(self):
        """Reset all metrics."""
        self._request_count = 0
        self._error_count = 0
        self._slow_request_count = 0
        self._endpoint_counts.clear()
        self._endpoint_errors.clear()
        self._endpoint_times.clear()
        self._slow_requests.clear()


# Global metrics instance
metrics = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for collecting metrics.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Get endpoint pattern
        endpoint = request.url.path
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Record metrics
        metrics.record_request(
            endpoint=endpoint,
            duration_ms=duration_ms,
            status_code=response.status_code
        )
        
        # Add timing header to response
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        
        return response


def get_metrics() -> dict:
    """Get current metrics."""
    return metrics.get_stats()


def get_slow_requests(limit: int = 10) -> list:
    """Get recent slow requests."""
    return list(metrics._slow_requests)[-limit:]


def set_slow_threshold(threshold_ms: float):
    """Set slow request threshold."""
    metrics._slow_threshold_ms = threshold_ms