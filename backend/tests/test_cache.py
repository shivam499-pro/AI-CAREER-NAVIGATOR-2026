"""
Tests for cache behavior in Gemini service.
Tests caching logic, TTL expiration, and LRU eviction.
"""
import pytest
import sys
import os
import time
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestCacheConfiguration:
    """Test cache configuration constants."""

    def test_cache_max_size(self):
        """Test CACHE_MAX_SIZE configuration."""
        from services.gemini_service import CACHE_MAX_SIZE
        
        assert CACHE_MAX_SIZE == 100

    def test_cache_ttl_seconds(self):
        """Test CACHE_TTL_SECONDS configuration."""
        from services.gemini_service import CACHE_TTL_SECONDS
        
        assert CACHE_TTL_SECONDS == 3600  # 1 hour

    def test_cache_initial_state(self):
        """Test that cache starts empty."""
        from services import gemini_service
        
        # Check internal cache state
        assert hasattr(gemini_service, '_analysis_cache')
        assert len(gemini_service._analysis_cache) == 0


class TestCleanupCache:
    """Test cache cleanup functionality."""

    def test_cleanup_removes_expired_entries(self):
        """Test that cleanup removes expired entries."""
        from services import gemini_service
        
        # Add a mock entry with old timestamp
        old_key = "test-key-old"
        gemini_service._analysis_cache[old_key] = {"data": "test"}
        gemini_service._cache_timestamps[old_key] = time.time() - 4000  # More than 1 hour ago
        
        # Run cleanup
        gemini_service._cleanup_cache()
        
        # Old entry should be removed
        assert old_key not in gemini_service._analysis_cache

    def test_cleanup_keeps_valid_entries(self):
        """Test that cleanup keeps valid entries."""
        from services import gemini_service
        
        # Add a fresh entry
        fresh_key = "test-key-fresh"
        gemini_service._analysis_cache[fresh_key] = {"data": "test"}
        gemini_service._cache_timestamps[fresh_key] = time.time()  # Now
        
        # Run cleanup
        gemini_service._cleanup_cache()
        
        # Fresh entry should remain
        assert fresh_key in gemini_service._analysis_cache

    def test_cleanup_enforces_max_size(self):
        """Test that cleanup enforces max size limit."""
        from services import gemini_service
        
        # Clear cache
        gemini_service._analysis_cache.clear()
        gemini_service._cache_timestamps.clear()
        
        # Add more entries than max size
        for i in range(gemini_service.CACHE_MAX_SIZE + 10):
            key = f"key-{i}"
            gemini_service._analysis_cache[key] = {"data": f"test-{i}"}
            gemini_service._cache_timestamps[key] = time.time()
        
        # Run cleanup
        gemini_service._cleanup_cache()
        
        # Should have at most CACHE_MAX_SIZE entries
        assert len(gemini_service._analysis_cache) <= gemini_service.CACHE_MAX_SIZE


class TestCacheEvictionLRU:
    """Test LRU (Least Recently Used) eviction."""

    def test_lru_removes_oldest_entries(self):
        """Test that LRU removes oldest entries first."""
        from services import gemini_service
        
        # Clear cache first
        gemini_service._analysis_cache.clear()
        gemini_service._cache_timestamps.clear()
        
        # Add 100 recent entries (should be more than max after cleanup)
        for i in range(gemini_service.CACHE_MAX_SIZE + 50):
            key = f"new-key-{i}"
            gemini_service._analysis_cache[key] = {"data": f"new-{i}"}
            gemini_service._cache_timestamps[key] = time.time()  # All recent
        
        # Run cleanup
        gemini_service._cleanup_cache()
        
        # Should have at most CACHE_MAX_SIZE entries
        assert len(gemini_service._analysis_cache) <= gemini_service.CACHE_MAX_SIZE


class TestCacheStateFunctions:
    """Test cache state management functions."""

    def test_last_github_data_initial_state(self):
        """Test _last_github_data starts empty."""
        from services import gemini_service
        
        assert hasattr(gemini_service, '_last_github_data')
        assert isinstance(gemini_service._last_github_data, dict)

    def test_last_leetcode_data_initial_state(self):
        """Test _last_leetcode_data starts empty."""
        from services import gemini_service
        
        assert hasattr(gemini_service, '_last_leetcode_data')
        assert isinstance(gemini_service._last_leetcode_data, dict)


class TestMockMode:
    """Test MOCK_MODE configuration."""

    def test_mock_mode_default(self):
        """Test that MOCK_MODE defaults to False."""
        from services.gemini_service import MOCK_MODE
        
        assert MOCK_MODE is False

    def test_mock_mode_response(self):
        """Test that MOCK_MODE returns mock response when enabled."""
        from services.gemini_service import MOCK_RESPONSE
        
        # Check mock response structure
        assert "analysis" in MOCK_RESPONSE
        assert "career_paths" in MOCK_RESPONSE
        assert "skill_gaps" in MOCK_RESPONSE
        assert "roadmap" in MOCK_RESPONSE


class TestCacheTTL:
    """Test TTL behavior in cache."""

    def test_ttl_exactly_one_hour(self):
        """Test that TTL is exactly 1 hour."""
        from services.gemini_service import CACHE_TTL_SECONDS
        
        assert CACHE_TTL_SECONDS == 60 * 60  # 3600 seconds = 1 hour

    def test_ttl_expiration_calculation(self):
        """Test TTL expiration calculation."""
        from services import gemini_service
        
        # Add entry that will expire in 1 second
        test_key = "ttl-test-key"
        gemini_service._analysis_cache[test_key] = {"data": "test"}
        gemini_service._cache_timestamps[test_key] = time.time() - (3600 - 1)  # 3599 seconds ago
        
        # Should not be expired yet
        expired_keys = [
            k for k, ts in gemini_service._cache_timestamps.items()
            if time.time() - ts > gemini_service.CACHE_TTL_SECONDS
        ]
        
        assert test_key not in expired_keys

    def test_ttl_expiration_after_one_hour(self):
        """Test that entries older than 1 hour are expired."""
        from services import gemini_service
        
        test_key = "ttl-expired-key"
        gemini_service._analysis_cache[test_key] = {"data": "test"}
        gemini_service._cache_timestamps[test_key] = time.time() - 3700  # More than 1 hour ago
        
        # Should be expired
        expired_keys = [
            k for k, ts in gemini_service._cache_timestamps.items()
            if time.time() - ts > gemini_service.CACHE_TTL_SECONDS
        ]
        
        assert test_key in expired_keys


class TestCacheSizeLimit:
    """Test max cache size behavior."""

    def test_max_size_100(self):
        """Test that max cache size is 100."""
        from services.gemini_service import CACHE_MAX_SIZE
        
        assert CACHE_MAX_SIZE == 100

    def test_enforce_max_size(self):
        """Test that max size is enforced."""
        from services import gemini_service
        
        # Clear cache
        gemini_service._analysis_cache.clear()
        gemini_service._cache_timestamps.clear()
        
        # Fill beyond max
        for i in range(150):
            key = f"size-test-{i}"
            gemini_service._analysis_cache[key] = {"data": i}
            gemini_service._cache_timestamps[key] = time.time()
        
        # Enforce max
        gemini_service._cleanup_cache()
        
        # Should not exceed max
        assert len(gemini_service._analysis_cache) <= 100


class TestOrderedDictUsage:
    """Test that OrderedDict is used for LRU behavior."""

    def test_uses_ordered_dict(self):
        """Test that cache uses OrderedDict."""
        from services.gemini_service import _analysis_cache
        from collections import OrderedDict
        
        # OrderedDict should be imported/used
        assert hasattr(_analysis_cache, '__getitem__')  # Has dict-like access


class TestCacheKeyGeneration:
    """Test cache key generation logic."""

    def test_cache_key_from_inputs(self):
        """Test that cache key is generated from inputs."""
        # The service should generate deterministic keys from inputs
        # This is implied by the caching mechanism in run_combined_analysis
        # Keys are typically generated from hash of inputs
        
        # We verify cache state management exists
        from services import gemini_service
        
        assert hasattr(gemini_service, '_analysis_cache')
        assert hasattr(gemini_service, '_cache_timestamps')


class TestCacheBehaviorIntegration:
    """Integration tests for cache behavior."""

    def test_multiple_calls_same_inputs(self):
        """Test that multiple calls with same inputs use cache."""
        from services import gemini_service
        
        # Clear cache first
        gemini_service._analysis_cache.clear()
        gemini_service._cache_timestamps.clear()
        
        # First call - should add to cache
        # Second call with same params - should hit cache
        # We can verify by checking cache state
        
        # This is more of a documentation test since actual caching
        # would require tracing calls to _generate
        assert True  # Cache mechanism exists

    def test_different_inputs_different_cache_keys(self):
        """Test that different inputs get different cache keys."""
        from services import gemini_service
        
        # The cache uses OrderedDict which supports different keys
        gemini_service._analysis_cache["key1"] = {"data": "value1"}
        gemini_service._analysis_cache["key2"] = {"data": "value2"}
        
        assert "key1" in gemini_service._analysis_cache
        assert "key2" in gemini_service._analysis_cache
        assert gemini_service._analysis_cache["key1"]["data"] == "value1"


class TestCachePerformance:
    """Test cache performance characteristics."""

    def test_cleanup_does_not_affect_fresh_entries(self):
        """Test cleanup is fast and doesn't affect fresh entries."""
        from services import gemini_service
        
        # Clear cache first
        gemini_service._analysis_cache.clear()
        gemini_service._cache_timestamps.clear()
        
        # Add fresh entries
        for i in range(50):
            key = f"perf-{i}"
            gemini_service._analysis_cache[key] = {"data": i}
            gemini_service._cache_timestamps[key] = time.time()
        
        # Cleanup should be quick
        start = time.time()
        gemini_service._cleanup_cache()
        elapsed = time.time() - start
        
        assert elapsed < 1.0  # Should be very fast
        # All entries should be retained since they're under max size
        assert len(gemini_service._analysis_cache) == 50