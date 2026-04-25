"""
Redis Caching Layer
Provides Redis caching with per-user keys, partial invalidation, and in-memory fallback.
"""
import json
import logging
import os
import time
from typing import Any, Optional, Union
from functools import wraps

logger = logging.getLogger(__name__)


class CacheClient:
    """
    Redis caching client with in-memory fallback.
    Supports per-user keys and partial invalidation.
    """
    
    def __init__(self):
        self._redis_client = None
        self._memory_cache = {}
        self._memory_expiry = {}
        self._use_redis = False
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._redis_client.ping()
            self._use_redis = True
            logger.info("Redis caching enabled")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self._use_redis = False
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=str)
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        return json.loads(value)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self._use_redis and self._redis_client:
            try:
                value = self._redis_client.get(key)
                if value:
                    return self._deserialize(value)
            except Exception as e:
                logger.warning(f"Redis get failed, using memory fallback: {e}")
        
        # Fallback to memory cache
        if key in self._memory_cache:
            expiry = self._memory_expiry.get(key, 0)
            if expiry > time.time():
                return self._memory_cache[key]
            else:
                # Clean up expired
                del self._memory_cache[key]
                if key in self._memory_expiry:
                    del self._memory_expiry[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL in seconds."""
        if self._use_redis and self._redis_client:
            try:
                serialized = self._serialize(value)
                self._redis_client.setex(key, ttl, serialized)
                return True
            except Exception as e:
                logger.warning(f"Redis set failed, using memory fallback: {e}")
        
        # Fallback to memory cache
        self._memory_cache[key] = value
        self._memory_expiry[key] = time.time() + ttl
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        
        # Also remove from memory
        if key in self._memory_cache:
            del self._memory_cache[key]
        if key in self._memory_expiry:
            del self._memory_expiry[key]
        
        return True
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        count = 0
        if self._use_redis and self._redis_client:
            try:
                keys = self._redis_client.keys(pattern)
                if keys:
                    count = self._redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis clear pattern failed: {e}")
        
        # Clear matching memory keys
        for key in list(self._memory_cache.keys()):
            if pattern.replace("*", "") in key:
                del self._memory_cache[key]
                if key in self._memory_expiry:
                    del self._memory_expiry[key]
                count += 1
        
        return count
    
    def invalidate_user_cache(self, user_id: str) -> int:
        """
        Invalidate all cache entries for a specific user.
        
        Args:
            user_id: User ID to invalidate cache for
        
        Returns:
            Number of keys invalidated
        """
        pattern = f"user:{user_id}:*"
        return self.clear_pattern(pattern)
    
    def invalidate_user_pattern(self, user_id: str, key_prefix: str) -> int:
        """
        Invalidate specific cache pattern for a user.
        
        Args:
            user_id: User ID
            key_prefix: Key prefix to match (e.g., "profile", "jobs")
        
        Returns:
            Number of keys invalidated
        """
        pattern = f"user:{user_id}:{key_prefix}:*"
        return self.clear_pattern(pattern)
    
    def get_user_cache_stats(self, user_id: str) -> dict:
        """
        Get cache statistics for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            dict with cache stats
        """
        pattern = f"user:{user_id}:*"
        count = 0
        if self._use_redis and self._redis_client:
            try:
                keys = self._redis_client.keys(pattern)
                count = len(keys) if keys else 0
            except Exception:
                pass
        
        # Count memory keys
        for key in self._memory_cache.keys():
            if key.startswith(f"user:{user_id}:"):
                count += 1
        
        return {
            "user_id": user_id,
            "cached_entries": count,
            "cache_type": "redis" if self._use_redis else "memory"
        }


# Global cache instance
cache = CacheClient()


def cached(key_prefix: str, ttl: int = 300):
    """
    Decorator to cache function results.
    
    Usage:
        @cached("user:profile:", ttl=600)
        async def get_user_profile(user_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from prefix + args
            cache_key = f"{key_prefix}"
            for arg in args:
                if isinstance(arg, str):
                    cache_key += f"{arg}:"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def cached_user(key_prefix: str, ttl: int = 300):
    """
    Decorator to cache function results with user-specific keys.
    Automatically includes user_id in the cache key.
    
    Usage:
        @cached_user("profile", ttl=600)
        async def get_user_profile(user_id: str):
            ...
    
    Results in key: user:{user_id}:profile:{...}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(user_id: str, *args, **kwargs):
            # Build user-specific cache key
            extra_parts = ":".join(str(arg) for arg in args if isinstance(arg, str))
            cache_key = f"user:{user_id}:{key_prefix}"
            if extra_parts:
                cache_key += f":{extra_parts}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(user_id, *args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    Decorator to invalidate cache after function execution.
    
    Usage:
        @invalidate_cache("user:profile:*")
        async def update_user_profile(user_id: str, data):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            # Invalidate matching keys
            cache.clear_pattern(pattern)
            return result
        
        return wrapper
    return decorator


def invalidate_user_cache_after(user_id_arg_pos: int = 0):
    """
    Decorator to invalidate user-specific cache after function execution.
    
    Usage:
        @invalidate_user_cache_after()  # user_id is first arg
        async def update_profile(user_id: str, data):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user_id from args
            user_id = args[user_id_arg_pos] if user_id_arg_pos < len(args) else kwargs.get('user_id')
            
            result = await func(*args, **kwargs)
            
            # Invalidate user cache
            if user_id:
                cache.invalidate_user_cache(user_id)
            
            return result
        
        return wrapper
    return decorator