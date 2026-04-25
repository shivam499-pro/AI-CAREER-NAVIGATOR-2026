"""
Circuit Breaker Pattern Implementation
Provides fault tolerance and resilience for external service calls.
"""
import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
        excluded_exceptions: tuple = ()
    ):
        self.failure_threshold = failure_threshold  # Failures before opening
        self.recovery_timeout = recovery_timeout    # Seconds before half-open
        self.half_open_max_calls = half_open_max_calls  # Max calls in half-open
        self.excluded_exceptions = excluded_exceptions  # Exceptions to ignore


class CircuitBreaker:
    """
    Circuit Breaker implementation for fault tolerance.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected
    - HALF_OPEN: Testing recovery, limited requests allowed
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current state, checking for recovery timeout."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.config.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state
    
    async def call(self, func: Callable, *args, fallback: Any = None, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            fallback: Value to return if circuit is open
            **kwargs: Keyword arguments
        
        Returns:
            Function result or fallback value
        """
        async with self._lock:
            current_state = self.state
            
            if current_state == CircuitState.OPEN:
                logger.warning(f"Circuit {self.name} is OPEN, rejecting call")
                return fallback
            
            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    logger.warning(f"Circuit {self.name} HALF_OPEN limit reached")
                    return fallback
                self._half_open_calls += 1
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # On success
            await self._on_success()
            return result
            
        except Exception as e:
            # Check if exception should be ignored
            if self.config.excluded_exceptions and isinstance(e, self.config.excluded_exceptions):
                logger.info(f"Circuit {self.name}: Ignoring excluded exception: {e}")
                return fallback
            
            # On failure
            await self._on_failure()
            logger.error(f"Circuit {self.name} call failed: {e}")
            return fallback
    
    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            self._failure_count = 0
            self._success_count += 1
            
            if self._state == CircuitState.HALF_OPEN:
                # After enough successes, close the circuit
                if self._success_count >= self.config.half_open_max_calls:
                    logger.info(f"Circuit {self.name} recovered, CLOSING")
                    self._state = CircuitState.CLOSED
                    self._success_count = 0
                    self._half_open_calls = 0
    
    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                logger.warning(f"Circuit {self.name} failure in HALF_OPEN, REOPENING")
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
                self._success_count = 0
                
            elif self._failure_count >= self.config.failure_threshold:
                logger.warning(f"Circuit {self.name} threshold reached, OPENING")
                self._state = CircuitState.OPEN
    
    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": datetime.fromtimestamp(self._last_failure_time, tz=timezone.utc).isoformat() if self._last_failure_time else None
        }
    
    async def reset(self):
        """Manually reset the circuit breaker."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            logger.info(f"Circuit {self.name} manually reset")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    def get_or_create(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_all_status(self) -> list:
        """Get status of all circuit breakers."""
        return [breaker.get_status() for breaker in self._breakers.values()]
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()


# Global registry
registry = CircuitBreakerRegistry()


# Decorator for easy circuit breaker usage
def circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    excluded_exceptions: tuple = ()
):
    """
    Decorator to add circuit breaker protection to async functions.
    
    Usage:
        @circuit_breaker("gemini", failure_threshold=3)
        async def call_gemini(prompt):
            ...
    """
    def decorator(func: Callable) -> Callable:
        circuit_name = name or func.__module__ + "." + func.__name__
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = registry.get_or_create(
                circuit_name,
                CircuitBreakerConfig(
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    excluded_exceptions=excluded_exceptions
                )
            )
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


# Pre-configured circuit breakers for common services
def get_gemini_circuit() -> CircuitBreaker:
    """Get circuit breaker for Gemini API."""
    return registry.get_or_create(
        "gemini",
        CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            excluded_exceptions=(ValueError, KeyError)  # Don't count programming errors
        )
    )


def get_supabase_circuit() -> CircuitBreaker:
    """Get circuit breaker for Supabase."""
    return registry.get_or_create(
        "supabase",
        CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=30
        )
    )


def get_external_api_circuit(api_name: str) -> CircuitBreaker:
    """Get circuit breaker for external APIs."""
    return registry.get_or_create(
        f"external:{api_name}",
        CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=120  # Longer for external APIs
        )
    )
