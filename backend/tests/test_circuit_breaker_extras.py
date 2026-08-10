"""
Companion tests for core/circuit_breaker.py.

tests/test_circuit_breaker.py already covers the core CLOSED -> OPEN ->
HALF_OPEN -> CLOSED state machine on a directly-constructed CircuitBreaker.
This file covers what it doesn't: the HALF_OPEN call-limit rejection, a
failure occurring *during* HALF_OPEN (reopening), get_status()/reset(),
the CircuitBreakerRegistry, the @circuit_breaker decorator, and the three
pre-configured convenience functions (get_gemini_circuit etc).
"""
import asyncio
import time
import pytest
import pytest_asyncio

from core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
    circuit_breaker,
    registry,
    get_gemini_circuit,
    get_supabase_circuit,
    get_external_api_circuit,
)


async def async_success():
    return "success"


async def async_failure():
    raise Exception("failure")


@pytest_asyncio.fixture(autouse=True)
async def cleanup_registry():
    """Isolate the global registry singleton between tests in this file too."""
    yield
    await registry.reset_all()
    registry._breakers.clear()


# =============================================================================
# HALF_OPEN call-limit rejection
# =============================================================================

class TestHalfOpenCallLimit:
    @pytest.mark.asyncio
    async def test_half_open_rejects_calls_beyond_max(self):
        config = CircuitBreakerConfig(
            failure_threshold=1, recovery_timeout=1, half_open_max_calls=1
        )
        breaker = CircuitBreaker("half-open-limit-test", config)

        # Force OPEN
        await breaker.call(async_failure, fallback="f")
        assert breaker.state == CircuitState.OPEN

        # Wait for HALF_OPEN eligibility
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # First call in HALF_OPEN is allowed to consume the single slot.
        # Use a slow coroutine so we can issue a second call while the
        # first is still "in flight" from the breaker's bookkeeping
        # perspective — simplest reliable way: exhaust the slot count
        # directly, then verify the next call is rejected outright.
        breaker._half_open_calls = config.half_open_max_calls  # slot already used up

        result = await breaker.call(async_success, fallback="blocked")

        assert result == "blocked"


# =============================================================================
# Failure occurring while HALF_OPEN
# =============================================================================

class TestFailureDuringHalfOpen:
    @pytest.mark.asyncio
    async def test_failure_in_half_open_reopens_circuit(self):
        """
        DOCUMENTS A REAL FINDING: _on_failure() updates _last_failure_time
        to "now" BEFORE checking `self.state`. Since the `state` property's
        OPEN -> HALF_OPEN promotion is based on elapsed time since
        _last_failure_time, that update resets the elapsed-time window to
        ~0 right before the check runs. With any realistic recovery_timeout
        (the codebase uses 30-120s), elapsed~0 is never >= recovery_timeout,
        so `self.state == HALF_OPEN` is always False at that check point —
        this branch (the dedicated "reopen from HALF_OPEN" path) is
        unreachable in practice. It only fires with recovery_timeout=0,
        which is what this test uses to exercise it at all. See the test
        below for what actually happens with a realistic recovery_timeout.
        """
        config = CircuitBreakerConfig(
            failure_threshold=1, recovery_timeout=0, half_open_max_calls=3
        )
        breaker = CircuitBreaker("half-open-failure-test", config)

        await breaker.call(async_failure, fallback="f")  # -> OPEN
        assert breaker._state == CircuitState.OPEN

        # With recovery_timeout=0, the very next state check already
        # reports HALF_OPEN (elapsed >= 0 is trivially true) — no sleep
        # needed.
        await breaker.call(async_failure, fallback="f")

        assert breaker._state == CircuitState.OPEN
        assert breaker._half_open_calls == 0
        assert breaker._success_count == 0

    @pytest.mark.asyncio
    async def test_realistic_recovery_timeout_reopens_via_threshold_branch_instead(self):
        """
        With a realistic (non-zero) recovery_timeout, a failure during
        HALF_OPEN does NOT take the dedicated reopen branch above — it
        falls through to the plain `failure_count >= threshold` branch
        instead, because _last_failure_time was just reset. The circuit
        still correctly reopens (_state becomes OPEN), but this path does
        NOT reset _half_open_calls/_success_count, unlike the dedicated
        branch. Those counters can carry over stale values into the next
        recovery cycle.
        """
        config = CircuitBreakerConfig(
            failure_threshold=1, recovery_timeout=1, half_open_max_calls=3
        )
        breaker = CircuitBreaker("realistic-half-open-failure", config)

        await breaker.call(async_failure, fallback="f")  # -> OPEN
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN  # via the property

        await breaker.call(async_failure, fallback="f")  # consumes a half-open slot, then fails

        assert breaker._state == CircuitState.OPEN  # still correctly reopened
        # ...but via the threshold branch, so these were NOT reset:
        assert breaker._half_open_calls == 1
        assert breaker._success_count == 0


# =============================================================================
# get_status()
# =============================================================================

class TestGetStatus:
    def test_status_before_any_calls(self):
        breaker = CircuitBreaker("status-fresh")
        status = breaker.get_status()

        assert status == {
            "name": "status-fresh",
            "state": "closed",
            "failure_count": 0,
            "success_count": 0,
            "last_failure": None,
        }

    @pytest.mark.asyncio
    async def test_status_reflects_failure_count_and_timestamp(self):
        breaker = CircuitBreaker(
            "status-after-failure",
            CircuitBreakerConfig(failure_threshold=5),
        )

        await breaker.call(async_failure, fallback="f")
        status = breaker.get_status()

        assert status["failure_count"] == 1
        assert status["state"] == "closed"  # threshold not reached yet
        assert status["last_failure"] is not None  # ISO timestamp string


# =============================================================================
# reset()
# =============================================================================

class TestReset:
    @pytest.mark.asyncio
    async def test_reset_clears_all_state(self):
        breaker = CircuitBreaker(
            "reset-test", CircuitBreakerConfig(failure_threshold=1)
        )

        await breaker.call(async_failure, fallback="f")
        assert breaker.state == CircuitState.OPEN

        await breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._success_count == 0
        assert breaker._last_failure_time is None
        assert breaker._half_open_calls == 0


# =============================================================================
# CircuitBreakerRegistry
# =============================================================================

class TestCircuitBreakerRegistry:
    def test_get_or_create_returns_new_breaker(self):
        reg = CircuitBreakerRegistry()
        breaker = reg.get_or_create("svc-a")

        assert isinstance(breaker, CircuitBreaker)
        assert breaker.name == "svc-a"

    def test_get_or_create_returns_same_instance_on_repeat_call(self):
        reg = CircuitBreakerRegistry()
        first = reg.get_or_create("svc-b")
        second = reg.get_or_create("svc-b")

        assert first is second

    def test_get_or_create_with_custom_config(self):
        reg = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=99)
        breaker = reg.get_or_create("svc-c", config)

        assert breaker.config.failure_threshold == 99

    def test_get_all_status_returns_status_for_every_breaker(self):
        reg = CircuitBreakerRegistry()
        reg.get_or_create("svc-d")
        reg.get_or_create("svc-e")

        statuses = reg.get_all_status()

        names = {s["name"] for s in statuses}
        assert names == {"svc-d", "svc-e"}

    @pytest.mark.asyncio
    async def test_reset_all_resets_every_breaker(self):
        reg = CircuitBreakerRegistry()
        b1 = reg.get_or_create("svc-f", CircuitBreakerConfig(failure_threshold=1))
        b2 = reg.get_or_create("svc-g", CircuitBreakerConfig(failure_threshold=1))

        await b1.call(async_failure, fallback="f")
        await b2.call(async_failure, fallback="f")
        assert b1.state == CircuitState.OPEN
        assert b2.state == CircuitState.OPEN

        await reg.reset_all()

        assert b1.state == CircuitState.CLOSED
        assert b2.state == CircuitState.CLOSED


# =============================================================================
# @circuit_breaker decorator
# =============================================================================

class TestCircuitBreakerDecorator:
    @pytest.mark.asyncio
    async def test_decorator_passes_through_successful_call(self):
        @circuit_breaker(name="decorated-success")
        async def do_thing(x):
            return x * 2

        result = await do_thing(21)

        assert result == 42

    @pytest.mark.asyncio
    async def test_decorator_uses_module_and_function_name_when_unnamed(self):
        @circuit_breaker()
        async def my_uniquely_named_function():
            return "ok"

        await my_uniquely_named_function()

        expected_name = f"{my_uniquely_named_function.__wrapped__.__module__}.my_uniquely_named_function"
        assert expected_name in registry._breakers

    @pytest.mark.asyncio
    async def test_decorator_registers_breaker_under_given_name(self):
        @circuit_breaker(name="my-custom-circuit", failure_threshold=2)
        async def do_thing():
            return "ok"

        await do_thing()

        assert "my-custom-circuit" in registry._breakers
        assert registry._breakers["my-custom-circuit"].config.failure_threshold == 2

    @pytest.mark.asyncio
    async def test_decorator_opens_after_threshold_and_returns_none_fallback(self):
        @circuit_breaker(name="decorated-failure", failure_threshold=2, recovery_timeout=60)
        async def always_fails():
            raise RuntimeError("nope")

        # No `fallback=` is passed through the decorator's call site, so
        # the CircuitBreaker.call default (fallback=None) applies.
        r1 = await always_fails()
        r2 = await always_fails()
        r3 = await always_fails()  # circuit now OPEN, short-circuits

        assert r1 is None
        assert r2 is None
        assert r3 is None
        assert registry._breakers["decorated-failure"].state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_decorator_respects_excluded_exceptions(self):
        @circuit_breaker(
            name="decorated-excluded",
            failure_threshold=1,
            excluded_exceptions=(ValueError,),
        )
        async def raises_value_error():
            raise ValueError("not a real failure")

        await raises_value_error()
        await raises_value_error()

        # ValueError is excluded, so the circuit should never open no
        # matter how many times it's raised.
        assert registry._breakers["decorated-excluded"].state == CircuitState.CLOSED


# =============================================================================
# Pre-configured circuit convenience functions
# =============================================================================

class TestPreconfiguredCircuits:
    def test_get_gemini_circuit_config(self):
        breaker = get_gemini_circuit()

        assert breaker.name == "gemini"
        assert breaker.config.failure_threshold == 5
        assert breaker.config.recovery_timeout == 60
        assert breaker.config.excluded_exceptions == (ValueError, KeyError)

    def test_get_gemini_circuit_returns_same_instance_across_calls(self):
        first = get_gemini_circuit()
        second = get_gemini_circuit()

        assert first is second

    def test_get_supabase_circuit_config(self):
        breaker = get_supabase_circuit()

        assert breaker.name == "supabase"
        assert breaker.config.failure_threshold == 10
        assert breaker.config.recovery_timeout == 30

    def test_get_external_api_circuit_config(self):
        breaker = get_external_api_circuit("serpapi")

        assert breaker.name == "external:serpapi"
        assert breaker.config.failure_threshold == 3
        assert breaker.config.recovery_timeout == 120

    def test_get_external_api_circuit_distinct_per_api_name(self):
        serp = get_external_api_circuit("serpapi")
        github = get_external_api_circuit("github")

        assert serp is not github
        assert serp.name != github.name