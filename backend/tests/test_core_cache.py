"""
Tests for core/cache.py — CacheClient and cache decorators.

NOTE: This is a NEW file, distinct from tests/test_cache.py (which tests
services/gemini_service.py's separate in-memory analysis cache, not this
module). Recommend renaming that file to tests/test_gemini_service_cache.py
so the name matches what it actually covers.

Every test here explicitly controls whether the Redis path or the
in-memory fallback path is exercised (by patching redis.from_url), so
these tests are deterministic regardless of whether a real Redis
instance happens to be reachable in the environment they run in.
"""
import time
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from core.cache import CacheClient


# =============================================================================
# Helpers
# =============================================================================

def make_redis_backed_client():
    """Build a CacheClient with a mocked, 'working' Redis backend."""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    with patch("redis.from_url", return_value=mock_redis):
        client = CacheClient()
    assert client._use_redis is True  # sanity check the fixture itself
    return client, mock_redis


def make_memory_only_client():
    """Build a CacheClient where Redis is unavailable (forces memory fallback)."""
    with patch("redis.from_url", side_effect=ConnectionError("no redis here")):
        client = CacheClient()
    assert client._use_redis is False  # sanity check the fixture itself
    return client


# =============================================================================
# _init_redis
# =============================================================================

class TestInitRedis:
    def test_redis_available_enables_redis_path(self):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        with patch("redis.from_url", return_value=mock_redis) as mock_from_url:
            client = CacheClient()

        assert client._use_redis is True
        assert client._redis_client is mock_redis
        mock_from_url.assert_called_once()

    def test_redis_unavailable_falls_back_to_memory(self):
        with patch("redis.from_url", side_effect=Exception("connection refused")):
            client = CacheClient()

        assert client._use_redis is False
        assert client._memory_cache == {}
        assert client._memory_expiry == {}

    def test_redis_ping_failure_falls_back_to_memory(self):
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("ping timeout")
        with patch("redis.from_url", return_value=mock_redis):
            client = CacheClient()

        assert client._use_redis is False

    def test_uses_redis_url_env_var(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://custom-host:6380/2")
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        with patch("redis.from_url", return_value=mock_redis) as mock_from_url:
            CacheClient()

        mock_from_url.assert_called_once_with(
            "redis://custom-host:6380/2", decode_responses=True
        )

    def test_defaults_to_localhost_when_no_env_var(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        with patch("redis.from_url", return_value=mock_redis) as mock_from_url:
            CacheClient()

        mock_from_url.assert_called_once_with(
            "redis://localhost:6379/0", decode_responses=True
        )


# =============================================================================
# _serialize / _deserialize
# =============================================================================

class TestSerialization:
    def test_serialize_round_trip(self):
        client = make_memory_only_client()
        original = {"a": 1, "b": [1, 2, 3], "c": None}
        serialized = client._serialize(original)
        assert isinstance(serialized, str)
        assert client._deserialize(serialized) == original

    def test_serialize_falls_back_to_str_for_non_json_types(self):
        client = make_memory_only_client()

        class Weird:
            def __str__(self):
                return "weird-object"

        serialized = client._serialize({"obj": Weird()})
        assert "weird-object" in serialized


# =============================================================================
# get()
# =============================================================================

class TestGet:
    def test_redis_hit_returns_deserialized_value(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.get.return_value = '{"foo": "bar"}'

        result = client.get("some-key")

        assert result == {"foo": "bar"}
        mock_redis.get.assert_called_once_with("some-key")

    def test_redis_miss_falls_through_to_memory_miss(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.get.return_value = None

        result = client.get("absent-key")

        assert result is None

    def test_redis_exception_falls_back_to_memory(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.get.side_effect = Exception("redis down")
        # Prime the memory fallback with a valid entry
        client._memory_cache["k"] = "memory-value"
        client._memory_expiry["k"] = time.time() + 100

        result = client.get("k")

        assert result == "memory-value"

    def test_memory_hit_unexpired(self):
        client = make_memory_only_client()
        client._memory_cache["k"] = {"v": 1}
        client._memory_expiry["k"] = time.time() + 100

        assert client.get("k") == {"v": 1}

    def test_memory_hit_expired_is_purged_and_returns_none(self):
        client = make_memory_only_client()
        client._memory_cache["k"] = {"v": 1}
        client._memory_expiry["k"] = time.time() - 1  # already expired

        result = client.get("k")

        assert result is None
        assert "k" not in client._memory_cache
        assert "k" not in client._memory_expiry

    def test_missing_key_returns_none(self):
        client = make_memory_only_client()
        assert client.get("never-set") is None


# =============================================================================
# set()
# =============================================================================

class TestSet:
    def test_redis_set_success_does_not_touch_memory(self):
        client, mock_redis = make_redis_backed_client()

        result = client.set("k", {"v": 1}, ttl=60)

        assert result is True
        mock_redis.setex.assert_called_once()
        args, _ = mock_redis.setex.call_args
        assert args[0] == "k"
        assert args[1] == 60
        assert client._deserialize(args[2]) == {"v": 1}
        # Redis path succeeded, so memory cache should stay empty
        assert client._memory_cache == {}

    def test_redis_set_failure_falls_back_to_memory(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.setex.side_effect = Exception("redis write failed")

        result = client.set("k", {"v": 1}, ttl=60)

        assert result is True
        assert client._memory_cache["k"] == {"v": 1}
        assert client._memory_expiry["k"] > time.time()

    def test_memory_only_set(self):
        client = make_memory_only_client()

        result = client.set("k", "value", ttl=10)

        assert result is True
        assert client._memory_cache["k"] == "value"
        assert client._memory_expiry["k"] == pytest.approx(time.time() + 10, abs=1)


# =============================================================================
# delete()
# =============================================================================

class TestDelete:
    def test_redis_delete_calls_redis_and_clears_memory(self):
        client, mock_redis = make_redis_backed_client()
        client._memory_cache["k"] = "v"
        client._memory_expiry["k"] = time.time() + 100

        result = client.delete("k")

        assert result is True
        mock_redis.delete.assert_called_once_with("k")
        assert "k" not in client._memory_cache
        assert "k" not in client._memory_expiry

    def test_redis_delete_exception_still_clears_memory(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.delete.side_effect = Exception("redis delete failed")
        client._memory_cache["k"] = "v"
        client._memory_expiry["k"] = time.time() + 100

        result = client.delete("k")

        assert result is True
        assert "k" not in client._memory_cache

    def test_memory_only_delete(self):
        client = make_memory_only_client()
        client._memory_cache["k"] = "v"
        client._memory_expiry["k"] = time.time() + 100

        assert client.delete("k") is True
        assert "k" not in client._memory_cache

    def test_delete_nonexistent_key_is_a_no_op(self):
        client = make_memory_only_client()
        assert client.delete("never-existed") is True


# =============================================================================
# clear_pattern()
# =============================================================================

class TestClearPattern:
    def test_redis_and_memory_counts_are_combined(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.keys.return_value = ["user:1:a", "user:1:b", "user:1:c"]
        mock_redis.delete.return_value = 3
        client._memory_cache = {"user:1:a": 1, "user:1:b": 2, "other:1:z": 3}

        count = client.clear_pattern("user:1:*")

        # 3 from redis + 2 memory keys matching "user:1:" substring
        assert count == 5
        assert "user:1:a" not in client._memory_cache
        assert "user:1:b" not in client._memory_cache
        assert "other:1:z" in client._memory_cache  # unaffected

    def test_redis_no_matching_keys(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.keys.return_value = []
        client._memory_cache = {}

        count = client.clear_pattern("user:1:*")

        assert count == 0
        mock_redis.delete.assert_not_called()

    def test_redis_exception_falls_back_to_memory_only_count(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.keys.side_effect = Exception("redis unreachable")
        client._memory_cache = {"user:2:x": 1}

        count = client.clear_pattern("user:2:*")

        assert count == 1
        assert "user:2:x" not in client._memory_cache

    def test_memory_only_pattern_matching(self):
        client = make_memory_only_client()
        client._memory_cache = {
            "user:5:profile": 1,
            "user:5:jobs": 2,
            "user:6:profile": 3,
        }
        client._memory_expiry = {k: time.time() + 100 for k in client._memory_cache}

        count = client.clear_pattern("user:5:*")

        assert count == 2
        assert "user:5:profile" not in client._memory_cache
        assert "user:5:jobs" not in client._memory_cache
        assert "user:6:profile" in client._memory_cache
        # Expiry entries for cleared keys should also be gone
        assert "user:5:profile" not in client._memory_expiry


# =============================================================================
# invalidate_user_cache / invalidate_user_pattern
# =============================================================================

class TestInvalidateHelpers:
    def test_invalidate_user_cache_builds_correct_pattern(self):
        client = make_memory_only_client()
        with patch.object(client, "clear_pattern", return_value=7) as mock_clear:
            result = client.invalidate_user_cache("user-123")

        mock_clear.assert_called_once_with("user:user-123:*")
        assert result == 7

    def test_invalidate_user_pattern_builds_correct_pattern(self):
        client = make_memory_only_client()
        with patch.object(client, "clear_pattern", return_value=2) as mock_clear:
            result = client.invalidate_user_pattern("user-123", "profile")

        mock_clear.assert_called_once_with("user:user-123:profile:*")
        assert result == 2


# =============================================================================
# get_user_cache_stats()
# =============================================================================

class TestUserCacheStats:
    def test_redis_backed_stats(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.keys.return_value = ["user:9:a", "user:9:b"]
        client._memory_cache = {"user:9:c": 1}

        stats = client.get_user_cache_stats("9")

        assert stats["user_id"] == "9"
        assert stats["cached_entries"] == 3  # 2 redis + 1 memory
        assert stats["cache_type"] == "redis"

    def test_redis_keys_exception_still_counts_memory(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.keys.side_effect = Exception("redis unreachable")
        client._memory_cache = {"user:9:c": 1}

        stats = client.get_user_cache_stats("9")

        assert stats["cached_entries"] == 1
        assert stats["cache_type"] == "redis"  # reflects _use_redis flag, not success

    def test_memory_only_stats(self):
        client = make_memory_only_client()
        client._memory_cache = {
            "user:9:a": 1,
            "user:9:b": 2,
            "user:10:a": 3,
        }

        stats = client.get_user_cache_stats("9")

        assert stats["cached_entries"] == 2
        assert stats["cache_type"] == "memory"

    def test_redis_keys_empty_list_counts_as_zero(self):
        client, mock_redis = make_redis_backed_client()
        mock_redis.keys.return_value = []
        client._memory_cache = {}

        stats = client.get_user_cache_stats("nobody")

        assert stats["cached_entries"] == 0


# =============================================================================
# @cached decorator
# =============================================================================

class TestCachedDecorator:
    @pytest.fixture(autouse=True)
    def isolated_cache(self, monkeypatch):
        """Give the module-level `cache` singleton used by decorators
        a clean, memory-only instance for each test, so decorator tests
        don't depend on (or pollute) real global cache state."""
        import core.cache as cache_module
        fresh = make_memory_only_client()
        monkeypatch.setattr(cache_module, "cache", fresh)
        return fresh

    async def test_cache_miss_then_hit(self):
        from core.cache import cached

        call_count = 0

        @cached("greeting:")
        async def greet(name):
            nonlocal call_count
            call_count += 1
            return f"hello {name}"

        first = await greet("fox")
        second = await greet("fox")

        assert first == "hello fox"
        assert second == "hello fox"
        assert call_count == 1  # underlying function only ran once

    async def test_different_string_args_get_different_keys(self):
        from core.cache import cached

        call_count = 0

        @cached("greeting:")
        async def greet(name):
            nonlocal call_count
            call_count += 1
            return f"hello {name}"

        await greet("fox")
        await greet("vixen")

        assert call_count == 2

    async def test_non_string_args_are_excluded_from_cache_key(self):
        """Documents actual behavior: only string positional args are used
        to build the cache key, so calls that differ only in a non-string
        arg (e.g. an int) collide on the same cache entry."""
        from core.cache import cached

        call_count = 0

        @cached("lookup:")
        async def fetch(name, page):
            nonlocal call_count
            call_count += 1
            return f"{name}-page-{page}"

        first = await fetch("fox", 1)
        second = await fetch("fox", 2)  # different int arg, same string arg

        assert call_count == 1
        assert first == second == "fox-page-1"  # second call served stale cache


# =============================================================================
# @cached_user decorator
# =============================================================================

class TestCachedUserDecorator:
    @pytest.fixture(autouse=True)
    def isolated_cache(self, monkeypatch):
        import core.cache as cache_module
        fresh = make_memory_only_client()
        monkeypatch.setattr(cache_module, "cache", fresh)
        return fresh

    async def test_builds_user_scoped_key_without_extra_args(self, isolated_cache):
        from core.cache import cached_user

        @cached_user("profile")
        async def get_profile(user_id):
            return {"user_id": user_id}

        await get_profile("u1")

        assert isolated_cache.get("user:u1:profile") == {"user_id": "u1"}

    async def test_builds_user_scoped_key_with_extra_args(self, isolated_cache):
        from core.cache import cached_user

        @cached_user("jobs")
        async def get_jobs(user_id, category):
            return [category]

        await get_jobs("u1", "backend")

        assert isolated_cache.get("user:u1:jobs:backend") == ["backend"]

    async def test_cache_hit_skips_function_call(self):
        from core.cache import cached_user

        call_count = 0

        @cached_user("profile")
        async def get_profile(user_id):
            nonlocal call_count
            call_count += 1
            return {"user_id": user_id}

        await get_profile("u1")
        await get_profile("u1")

        assert call_count == 1


# =============================================================================
# @invalidate_cache decorator
# =============================================================================

class TestInvalidateCacheDecorator:
    async def test_clears_pattern_after_function_runs(self):
        from core.cache import invalidate_cache
        import core.cache as cache_module

        mock_cache = MagicMock()
        with patch.object(cache_module, "cache", mock_cache):
            @invalidate_cache("user:*:profile:*")
            async def update_profile(user_id):
                return {"updated": user_id}

            result = await update_profile("u1")

        assert result == {"updated": "u1"}
        mock_cache.clear_pattern.assert_called_once_with("user:*:profile:*")


# =============================================================================
# @invalidate_user_cache_after decorator
# =============================================================================

class TestInvalidateUserCacheAfterDecorator:
    async def test_invalidates_using_default_first_positional_arg(self):
        from core.cache import invalidate_user_cache_after
        import core.cache as cache_module

        mock_cache = MagicMock()
        with patch.object(cache_module, "cache", mock_cache):
            @invalidate_user_cache_after()
            async def update_profile(user_id, data):
                return {"ok": True}

            await update_profile("u1", {"name": "Fox"})

        mock_cache.invalidate_user_cache.assert_called_once_with("u1")

    async def test_invalidates_using_custom_arg_position(self):
        from core.cache import invalidate_user_cache_after
        import core.cache as cache_module

        mock_cache = MagicMock()
        with patch.object(cache_module, "cache", mock_cache):
            @invalidate_user_cache_after(user_id_arg_pos=1)
            async def update_profile(data, user_id):
                return {"ok": True}

            await update_profile({"name": "Fox"}, "u1")

        mock_cache.invalidate_user_cache.assert_called_once_with("u1")

    async def test_falls_back_to_user_id_kwarg(self):
        from core.cache import invalidate_user_cache_after
        import core.cache as cache_module

        mock_cache = MagicMock()
        with patch.object(cache_module, "cache", mock_cache):
            @invalidate_user_cache_after(user_id_arg_pos=5)  # out of range
            async def update_profile(**kwargs):
                return {"ok": True}

            await update_profile(user_id="u1")

        mock_cache.invalidate_user_cache.assert_called_once_with("u1")

    async def test_no_user_id_found_skips_invalidation(self):
        from core.cache import invalidate_user_cache_after
        import core.cache as cache_module

        mock_cache = MagicMock()
        with patch.object(cache_module, "cache", mock_cache):
            @invalidate_user_cache_after(user_id_arg_pos=5)  # out of range
            async def do_something():
                return {"ok": True}

            await do_something()

        mock_cache.invalidate_user_cache.assert_not_called()