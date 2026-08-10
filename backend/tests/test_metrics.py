"""
Tests for core/metrics.py — MetricsCollector, MetricsMiddleware, and the
module-level helper functions. There was previously no dedicated test file
for this module at all.
"""
import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.metrics import (
    MetricsCollector,
    MetricsMiddleware,
    metrics,
    get_metrics,
    get_slow_requests,
    set_slow_threshold,
)


# ─── MetricsCollector.record_request ───────────────────────────────────────

def test_record_request_increments_total_and_endpoint_counts():
    collector = MetricsCollector()

    collector.record_request("/api/foo", duration_ms=50.0, status_code=200)

    stats = collector.get_stats()
    assert stats["total_requests"] == 1
    assert stats["by_endpoint"] == {"/api/foo": 1}
    assert stats["total_errors"] == 0


def test_record_request_counts_4xx_and_5xx_as_errors():
    collector = MetricsCollector()

    collector.record_request("/api/foo", duration_ms=10.0, status_code=404)
    collector.record_request("/api/foo", duration_ms=10.0, status_code=500)
    collector.record_request("/api/foo", duration_ms=10.0, status_code=200)

    stats = collector.get_stats()
    assert stats["total_errors"] == 2
    assert stats["errors_by_endpoint"] == {"/api/foo": 2}


def test_record_request_flags_slow_requests_over_threshold():
    collector = MetricsCollector()
    collector._slow_threshold_ms = 100

    collector.record_request("/api/slow", duration_ms=250.0, status_code=200)

    stats = collector.get_stats()
    assert stats["slow_requests"] == 1
    assert len(stats["recent_slow_requests"]) == 1
    slow_entry = stats["recent_slow_requests"][0]
    assert slow_entry["endpoint"] == "/api/slow"
    assert slow_entry["duration_ms"] == 250.0
    assert slow_entry["status_code"] == 200
    assert "timestamp" in slow_entry


def test_record_request_under_threshold_is_not_flagged_as_slow():
    collector = MetricsCollector()
    collector._slow_threshold_ms = 3000

    collector.record_request("/api/fast", duration_ms=10.0, status_code=200)

    stats = collector.get_stats()
    assert stats["slow_requests"] == 0
    assert stats["recent_slow_requests"] == []


# ─── MetricsCollector.get_stats ─────────────────────────────────────────────

def test_get_stats_computes_average_response_time_per_endpoint():
    collector = MetricsCollector()

    collector.record_request("/api/foo", duration_ms=100.0, status_code=200)
    collector.record_request("/api/foo", duration_ms=200.0, status_code=200)

    stats = collector.get_stats()
    assert stats["avg_response_time_ms"]["/api/foo"] == 150.0


def test_get_stats_error_rate_is_zero_when_no_requests():
    collector = MetricsCollector()

    stats = collector.get_stats()

    assert stats["total_requests"] == 0
    assert stats["error_rate"] == 0.0


def test_get_stats_error_rate_calculation():
    collector = MetricsCollector()
    collector.record_request("/a", duration_ms=1.0, status_code=200)
    collector.record_request("/a", duration_ms=1.0, status_code=500)

    stats = collector.get_stats()

    assert stats["error_rate"] == 50.0


def test_get_stats_includes_slow_threshold():
    collector = MetricsCollector()
    collector._slow_threshold_ms = 1234

    stats = collector.get_stats()

    assert stats["slow_threshold_ms"] == 1234


# ─── MetricsCollector.reset ─────────────────────────────────────────────────

def test_reset_clears_all_counters_and_history():
    collector = MetricsCollector()
    collector.record_request("/api/foo", duration_ms=5000.0, status_code=500)

    collector.reset()

    stats = collector.get_stats()
    assert stats["total_requests"] == 0
    assert stats["total_errors"] == 0
    assert stats["slow_requests"] == 0
    assert stats["by_endpoint"] == {}
    assert stats["errors_by_endpoint"] == {}
    assert stats["avg_response_time_ms"] == {}
    assert stats["recent_slow_requests"] == []


# ─── Module-level helper functions ─────────────────────────────────────────

def test_get_metrics_returns_the_global_collectors_stats():
    metrics.reset()
    metrics.record_request("/api/global", duration_ms=5.0, status_code=200)

    result = get_metrics()

    assert result["total_requests"] == 1
    assert result["by_endpoint"] == {"/api/global": 1}

    metrics.reset()


def test_get_slow_requests_returns_recent_slow_requests_up_to_limit():
    metrics.reset()
    metrics._slow_threshold_ms = 0  # everything counts as slow for this test
    for i in range(5):
        metrics.record_request(f"/api/{i}", duration_ms=10.0, status_code=200)

    result = get_slow_requests(limit=2)

    assert len(result) == 2
    assert result[-1]["endpoint"] == "/api/4"

    metrics._slow_threshold_ms = 3000
    metrics.reset()


def test_get_slow_requests_defaults_to_10():
    metrics.reset()
    metrics._slow_threshold_ms = 0
    for i in range(15):
        metrics.record_request(f"/api/{i}", duration_ms=10.0, status_code=200)

    result = get_slow_requests()

    assert len(result) == 10

    metrics._slow_threshold_ms = 3000
    metrics.reset()


def test_set_slow_threshold_updates_the_global_collector():
    original = metrics._slow_threshold_ms
    try:
        set_slow_threshold(500)
        assert metrics._slow_threshold_ms == 500
    finally:
        metrics._slow_threshold_ms = original


# ─── MetricsMiddleware ──────────────────────────────────────────────────────

@pytest.fixture
def middleware_app():
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    @app.get("/boom")
    async def boom():
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="boom")

    return app


def test_middleware_records_request_and_adds_timing_header(middleware_app):
    metrics.reset()
    client = TestClient(middleware_app)

    response = client.get("/ping")

    assert response.status_code == 200
    assert "X-Response-Time-Ms" in response.headers
    stats = metrics.get_stats()
    assert stats["by_endpoint"].get("/ping") == 1

    metrics.reset()


def test_middleware_records_error_status_codes(middleware_app):
    metrics.reset()
    client = TestClient(middleware_app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    stats = metrics.get_stats()
    assert stats["errors_by_endpoint"].get("/boom") == 1

    metrics.reset()