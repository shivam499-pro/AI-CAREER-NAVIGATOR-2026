"""
Tests for celery_config.py

Coverage targets (36 missing lines → 100%):
- celery_app configuration values
- TaskWithRetry.on_failure / on_retry / on_success callbacks
- health_check_task
- cleanup_old_jobs: success path, exception path
"""
import pytest
from unittest.mock import MagicMock, patch, call
import logging


# ===========================================================================
# celery_app configuration
# ===========================================================================


class TestCeleryAppConfiguration:
    """Verify the Celery app is configured correctly."""

    def test_celery_app_name(self):
        from celery_config import celery_app
        assert celery_app.main == "career_navigator"

    def test_task_serializer_is_json(self):
        from celery_config import celery_app
        assert celery_app.conf.task_serializer == "json"

    def test_accept_content_is_json(self):
        from celery_config import celery_app
        assert "json" in celery_app.conf.accept_content

    def test_result_serializer_is_json(self):
        from celery_config import celery_app
        assert celery_app.conf.result_serializer == "json"

    def test_timezone_is_utc(self):
        from celery_config import celery_app
        assert celery_app.conf.timezone == "UTC"

    def test_enable_utc_is_true(self):
        from celery_config import celery_app
        assert celery_app.conf.enable_utc is True

    def test_task_acks_late(self):
        from celery_config import celery_app
        assert celery_app.conf.task_acks_late is True

    def test_task_reject_on_worker_lost(self):
        from celery_config import celery_app
        assert celery_app.conf.task_reject_on_worker_lost is True

    def test_task_track_started(self):
        from celery_config import celery_app
        assert celery_app.conf.task_track_started is True

    def test_task_time_limit(self):
        from celery_config import celery_app
        assert celery_app.conf.task_time_limit == 3600

    def test_task_soft_time_limit(self):
        from celery_config import celery_app
        assert celery_app.conf.task_soft_time_limit == 3000

    def test_worker_prefetch_multiplier(self):
        from celery_config import celery_app
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_worker_max_tasks_per_child(self):
        from celery_config import celery_app
        assert celery_app.conf.worker_max_tasks_per_child == 100

    def test_result_expires(self):
        from celery_config import celery_app
        assert celery_app.conf.result_expires == 86400

    def test_task_routes_contain_analysis_queue(self):
        from celery_config import celery_app
        routes = celery_app.conf.task_routes
        assert "services.async_job_service.process_analysis_job" in routes
        assert routes["services.async_job_service.process_analysis_job"]["queue"] == "analysis"

    def test_task_routes_contain_resume_queue(self):
        from celery_config import celery_app
        routes = celery_app.conf.task_routes
        assert "services.resume_service.process_resume" in routes
        assert routes["services.resume_service.process_resume"]["queue"] == "resume"

    def test_beat_schedule_has_cleanup_job(self):
        from celery_config import celery_app
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-old-jobs" in schedule
        assert schedule["cleanup-old-jobs"]["task"] == "services.async_job_service.cleanup_old_jobs"

    def test_beat_schedule_has_market_data_job(self):
        from celery_config import celery_app
        schedule = celery_app.conf.beat_schedule
        assert "update-market-data" in schedule
        assert schedule["update-market-data"]["task"] == "services.market_analyzer.update_market_data"

    def test_included_modules(self):
        from celery_config import celery_app
        includes = celery_app.conf.include
        assert "services.async_job_service" in includes
        assert "services.analysis_service" in includes
        assert "services.resume_service" in includes


# ===========================================================================
# TaskWithRetry — callback methods
# ===========================================================================


class TestTaskWithRetry:
    """
    TaskWithRetry extends celery.app.task.Task. The base Task.on_failure,
    on_retry, and on_success methods are plain no-ops in Celery (they do
    not touch the broker, backend, or any request context), so we can
    instantiate TaskWithRetry directly and call these callbacks with
    plain Python args — no broker connection, no try/except needed.

    If any of these calls raise in your environment, that itself is a
    real bug worth seeing — do not silently swallow it.
    """

    def test_on_failure_logs_error_with_task_id_and_exception(self):
        from celery_config import TaskWithRetry

        task = TaskWithRetry()
        exc = ValueError("something went wrong")
        einfo = MagicMock()

        with patch("celery_config.logger") as mock_logger:
            task.on_failure(exc, "task-id-1", [], {}, einfo)

        mock_logger.error.assert_called_once()
        logged_message = mock_logger.error.call_args[0][0]
        assert "task-id-1" in logged_message
        assert "something went wrong" in logged_message

    def test_on_retry_logs_warning_with_task_id_and_exception(self):
        from celery_config import TaskWithRetry

        task = TaskWithRetry()
        exc = ConnectionError("retry me")
        einfo = MagicMock()

        with patch("celery_config.logger") as mock_logger:
            task.on_retry(exc, "task-id-2", [], {}, einfo)

        mock_logger.warning.assert_called_once()
        logged_message = mock_logger.warning.call_args[0][0]
        assert "task-id-2" in logged_message
        assert "retry me" in logged_message

    def test_on_success_logs_info_with_task_id(self):
        from celery_config import TaskWithRetry

        task = TaskWithRetry()

        with patch("celery_config.logger") as mock_logger:
            task.on_success({"result": "ok"}, "task-id-3", [], {})

        mock_logger.info.assert_called_once()
        logged_message = mock_logger.info.call_args[0][0]
        assert "task-id-3" in logged_message

    def test_on_failure_calls_super_without_raising(self):
        """Base Task.on_failure is a no-op — calling it must not raise."""
        from celery_config import TaskWithRetry

        task = TaskWithRetry()
        with patch("celery_config.logger"):
            # No exception should propagate from super().on_failure()
            task.on_failure(Exception("x"), "tid", [], {}, MagicMock())

    def test_on_retry_calls_super_without_raising(self):
        from celery_config import TaskWithRetry

        task = TaskWithRetry()
        with patch("celery_config.logger"):
            task.on_retry(Exception("x"), "tid", [], {}, MagicMock())

    def test_on_success_calls_super_without_raising(self):
        from celery_config import TaskWithRetry

        task = TaskWithRetry()
        with patch("celery_config.logger"):
            task.on_success({"ok": True}, "tid", [], {})

    def test_autoretry_for_is_set(self):
        from celery_config import TaskWithRetry
        assert Exception in TaskWithRetry.autoretry_for

    def test_retry_backoff_is_enabled(self):
        from celery_config import TaskWithRetry
        assert TaskWithRetry.retry_backoff is True

    def test_retry_jitter_is_enabled(self):
        """
        Source bug FIXED: celery_config.py's TaskWithRetry previously had
        trailing commas on retry_backoff, retry_backoff_max, and
        retry_jitter, which silently turned them into 1-element tuples
        instead of scalars. That has been corrected — retry_jitter is now
        a plain boolean.
        """
        from celery_config import TaskWithRetry
        assert TaskWithRetry.retry_jitter is True


# ===========================================================================
# health_check_task
# ===========================================================================


class TestHealthCheckTask:
    """
    health_check_task is a BOUND task (bind=True), wrapped by Celery into
    a Task instance. `.run` is already a bound method on that instance —
    `self` is implicit, so we must NOT pass a second positional `self`.
    To control `self.request.hostname` inside the function body, we use
    Celery's documented `push_request()` / `pop_request()` pair on the
    task instance, wrapped in try/finally, to simulate a request context
    without a running worker.

    Historical note: test_health_check_task_is_registered previously
    failed with a TypeError from Celery's internal retry/backoff
    validation, caused by the retry_jitter/retry_backoff trailing-comma
    bug in TaskWithRetry (now fixed in celery_config.py).
    """

    def test_health_check_task_is_registered(self):
        from celery_config import celery_app
        registered = list(celery_app.tasks.keys())
        assert any("health_check_task" in name for name in registered)

    def test_health_check_task_returns_healthy_status(self):
        from celery_config import health_check_task

        health_check_task.push_request(hostname="worker@localhost")
        try:
            result = health_check_task.run()
        finally:
            health_check_task.pop_request()

        assert result["status"] == "healthy"

    def test_health_check_task_includes_worker_hostname(self):
        from celery_config import health_check_task

        health_check_task.push_request(hostname="celery@prod-worker-1")
        try:
            result = health_check_task.run()
        finally:
            health_check_task.pop_request()

        assert result["worker"] == "celery@prod-worker-1"


# ===========================================================================
# cleanup_old_jobs task
# ===========================================================================


class TestCleanupOldJobs:
    """
    cleanup_old_jobs is a plain (unbound) @celery_app.task. Calling
    cleanup_old_jobs.run() executes the task body directly, no broker
    needed.

    IMPORTANT: in the current source, `from datetime import ...` is
    OUTSIDE the try block, but `from services.async_job_service import
    async_job_service` is INSIDE it. To deterministically hit the
    `except Exception as e:` branch we must break the import that is
    actually inside try — breaking datetime instead would raise an
    uncaught ImportError straight out of the function, never reaching
    the except block (this was confirmed by an earlier failed attempt).
    """

    def test_cleanup_returns_cleaned_count_on_success(self):
        from celery_config import cleanup_old_jobs

        with patch("celery_config.logger"):
            result = cleanup_old_jobs.run()

        assert result == {"cleaned": 0}

    def test_cleanup_logs_info_with_cutoff_date(self):
        from celery_config import cleanup_old_jobs

        with patch("celery_config.logger") as mock_logger:
            cleanup_old_jobs.run()

        mock_logger.info.assert_called_once()
        assert "Cleaning up" in mock_logger.info.call_args[0][0]

    def test_cleanup_returns_error_dict_when_exception_raised(self):
        """
        CORRECTIONS from earlier attempts:
        1. Both `from datetime import ...` and `from services.async_job_service
           import ...` execute BEFORE `try:` in the source — breaking either
           import makes the exception escape the function entirely instead
           of being caught (confirmed by a prior failing test run).
        2. `datetime.datetime.now` is a C-extension method and cannot be
           patched directly with patch.object — it raises
           "can't set attributes of built-in/extension type 'datetime.datetime'"
           (confirmed via Celery/Python community references).

        The only statement genuinely inside `try` that can raise is the
        cutoff_date computation. Since `cleanup_old_jobs` does a LOCAL
        `from datetime import datetime, timedelta, timezone` import inside
        the function body, we replace the `datetime` entry in sys.modules
        with a fake module object (a plain mutable Python object, not the
        C type) whose `.now()` raises. This is the standard workaround for
        mocking datetime.now in exactly this situation.
        """
        from celery_config import cleanup_old_jobs
        import datetime as real_datetime_module
        import types

        fake_datetime_module = types.ModuleType("datetime")
        fake_datetime_module.timedelta = real_datetime_module.timedelta
        fake_datetime_module.timezone = real_datetime_module.timezone

        class FakeDatetimeClass:
            @classmethod
            def now(cls, tz=None):
                raise Exception("simulated clock failure")

        fake_datetime_module.datetime = FakeDatetimeClass

        with patch("celery_config.logger") as mock_logger:
            with patch.dict("sys.modules", {"datetime": fake_datetime_module}):
                result = cleanup_old_jobs.run()

        assert "error" in result
        assert "simulated clock failure" in result["error"]
        mock_logger.error.assert_called_once()
        assert "Cleanup failed" in mock_logger.error.call_args[0][0]

    def test_cleanup_task_is_registered(self):
        from celery_config import celery_app
        registered = list(celery_app.tasks.keys())
        assert any("cleanup_old_jobs" in name for name in registered)


# ===========================================================================
# REDIS_URL environment variable
# ===========================================================================


class TestRedisUrlConfiguration:
    """
    These tests reload celery_config to re-evaluate REDIS_URL under
    different environment conditions. The module is imported BEFORE
    the try block so that if anything inside try fails, `celery_config`
    is still a bound name and the finally block can safely restore state.
    """

    def test_default_redis_url_is_localhost(self):
        """When REDIS_URL is not set, defaults to localhost."""
        import os
        import importlib
        import celery_config

        original = os.environ.pop("REDIS_URL", None)
        try:
            importlib.reload(celery_config)
            assert "redis://localhost:6379/0" in celery_config.REDIS_URL
        finally:
            if original is not None:
                os.environ["REDIS_URL"] = original
            importlib.reload(celery_config)

    def test_custom_redis_url_is_used(self):
        """When REDIS_URL is set, it's used for broker and backend."""
        import os
        import importlib
        import celery_config

        original = os.environ.get("REDIS_URL")
        os.environ["REDIS_URL"] = "redis://prod-redis:6379/1"
        try:
            importlib.reload(celery_config)
            assert celery_config.REDIS_URL == "redis://prod-redis:6379/1"
        finally:
            if original is not None:
                os.environ["REDIS_URL"] = original
            else:
                os.environ.pop("REDIS_URL", None)
            importlib.reload(celery_config)