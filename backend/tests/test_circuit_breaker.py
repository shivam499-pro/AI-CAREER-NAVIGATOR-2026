import asyncio
import pytest
import time
import pytest_asyncio
from core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    registry,
)


# ----------------------------
# Helpers
# ----------------------------

async def async_success():
    return "success"


async def async_failure():
    raise Exception("failure")


def sync_success():
    return "sync_success"


def sync_failure():
    raise Exception("sync_failure")


# ----------------------------
# Fixtures
# ----------------------------

@pytest_asyncio.fixture
async def breaker():
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1,   # keep short for tests
        half_open_max_calls=2
    )
    return CircuitBreaker("test-breaker", config)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_registry():
    """Ensure isolation between tests."""
    yield
    await registry.reset_all()


# ----------------------------
# 1. CLOSED state - success path
# ----------------------------

@pytest.mark.asyncio
async def test_circuit_closed_allows_calls(breaker):
    result = await breaker.call(async_success)

    assert result == "success"
    assert breaker.state == CircuitState.CLOSED
    assert breaker._failure_count == 0


# ----------------------------
# 2. OPEN state after failures
# ----------------------------

@pytest.mark.asyncio
async def test_circuit_opens_after_threshold(breaker):
    # trigger failures
    for _ in range(3):
        await breaker.call(async_failure, fallback="fallback")

    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_open_circuit_rejects_calls(breaker):
    for _ in range(3):
        await breaker.call(async_failure, fallback="fallback")

    # should be open now
    result = await breaker.call(async_success, fallback="blocked")

    assert result == "blocked"
    assert breaker.state == CircuitState.OPEN


# ----------------------------
# 3. HALF-OPEN state (timeout-based)
# ----------------------------

@pytest.mark.asyncio
async def test_half_open_allows_test_calls(breaker):
    # force open
    for _ in range(3):
        await breaker.call(async_failure, fallback="fallback")

    assert breaker.state == CircuitState.OPEN

    # wait for recovery timeout
    await asyncio.sleep(1.1)

    # now state should be HALF_OPEN automatically
    assert breaker.state == CircuitState.HALF_OPEN

    # allow test call
    result = await breaker.call(async_success)

    assert result == "success"


# ----------------------------
# 4. Recovery back to CLOSED
# ----------------------------

@pytest.mark.asyncio
async def test_recovery_to_closed_state(breaker):
    # force open
    for _ in range(3):
        await breaker.call(async_failure, fallback="fallback")

    await asyncio.sleep(1.1)

    # half-open successful calls
    await breaker.call(async_success)
    await breaker.call(async_success)

    await asyncio.sleep(0.05)  # allow state updates
    assert breaker.state == CircuitState.CLOSED


# ----------------------------
# 5. Failure threshold config
# ----------------------------

@pytest.mark.asyncio
async def test_failure_threshold_respected():
    custom = CircuitBreaker(
        "custom",
        CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)
    )

    await custom.call(async_failure, fallback=None)
    assert custom.state == CircuitState.CLOSED

    await custom.call(async_failure, fallback=None)

    assert custom.state == CircuitState.OPEN


# ----------------------------
# 6. Sync function support
# ----------------------------

@pytest.mark.asyncio
async def test_sync_function_support(breaker):
    result = await breaker.call(sync_success)
    assert result == "sync_success"


# ----------------------------
# 7. Concurrent access safety
# ----------------------------

@pytest.mark.asyncio
async def test_concurrent_calls_thread_safety(breaker):
    async def flaky():
        if time.time() % 2 < 1:
            return "ok"
        raise Exception("fail")

    tasks = [
        breaker.call(flaky, fallback="fallback")
        for _ in range(20)
    ]

    results = await asyncio.gather(*tasks)

    # ensure system doesn't crash or deadlock
    assert len(results) == 20


# ----------------------------
# 8. Excluded exceptions should not count as failures
# ----------------------------

@pytest.mark.asyncio
async def test_excluded_exceptions_not_counted():
    config = CircuitBreakerConfig(
        failure_threshold=2,
        excluded_exceptions=(ValueError,)
    )

    breaker = CircuitBreaker("excluded-test", config)

    async def raise_value_error():
        raise ValueError("ignored")

    await breaker.call(raise_value_error, fallback="ok")
    await breaker.call(raise_value_error, fallback="ok")

    # should NOT open circuit
    assert breaker.state == CircuitState.CLOSED