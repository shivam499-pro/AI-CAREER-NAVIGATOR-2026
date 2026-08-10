"""
Tests for services/async_job_service.py

This service previously had NO dedicated test file. Whatever coverage it
had came entirely as incidental fallout from routers/analysis.py's
contract tests calling process_analysis_job() indirectly via a
background task -- meaning most of its real logic (idempotency keys,
duplicate-detection, job creation, status transitions, the module-level
wrapper functions) was never actually exercised directly, and a refactor
of the router could silently drop that coverage without anyone noticing.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from services.async_job_service import (
    AsyncJobService,
    JobStatus,
    JobType,
    async_job_service,
    create_analysis_job,
    create_analysis_job_idempotent,
    get_job_status,
    get_user_job_history,
)


def mock_supabase(mocker, return_data=None, count_data=None):
    """Wire up a mock Supabase client whose .execute() returns return_data
    by default. If count_data is provided, the FIRST .execute() call
    (used for the duplicate-check query) returns count_data instead,
    and subsequent calls return return_data (used for the create-job
    insert that follows)."""
    mock_client = MagicMock()
    execute_mock = MagicMock()

    if count_data is not None:
        execute_mock.execute.side_effect = [
            MagicMock(data=count_data),
            MagicMock(data=return_data),
        ]
    else:
        execute_mock.execute.return_value = MagicMock(data=return_data)

    # cover every chain shape used across the service's methods
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.gte.return_value.execute = execute_mock.execute
    mock_client.table.return_value.insert.return_value.execute = execute_mock.execute
    mock_client.table.return_value.select.return_value.eq.return_value.execute = execute_mock.execute
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute = execute_mock.execute
    mock_client.table.return_value.update.return_value.eq.return_value.execute = execute_mock.execute

    mocker.patch("services.async_job_service.get_supabase", return_value=mock_client)
    return mock_client


# ==========================================================
# _generate_idempotency_key: pure logic, no I/O
# ==========================================================

def test_generate_idempotency_key_is_deterministic():
    service = AsyncJobService()

    key1 = service._generate_idempotency_key(JobType.ANALYSIS, "user-1", {"a": 1})
    key2 = service._generate_idempotency_key(JobType.ANALYSIS, "user-1", {"a": 1})

    assert key1 == key2
    assert key1.startswith("analysis:user-1:")


def test_generate_idempotency_key_differs_by_payload():
    service = AsyncJobService()

    key1 = service._generate_idempotency_key(JobType.ANALYSIS, "user-1", {"a": 1})
    key2 = service._generate_idempotency_key(JobType.ANALYSIS, "user-1", {"a": 2})

    assert key1 != key2


# ==========================================================
# ensure_single_job
# ==========================================================

@pytest.mark.asyncio
async def test_ensure_single_job_returns_existing_when_duplicate_found(mocker):
    mock_supabase(mocker, count_data=[{"id": "existing-job", "status": "pending"}])
    service = AsyncJobService()

    job, is_new = await service.ensure_single_job(JobType.ANALYSIS, "user-1", {"a": 1})

    assert job == {"id": "existing-job", "status": "pending"}
    assert is_new is False


@pytest.mark.asyncio
async def test_ensure_single_job_creates_new_when_no_duplicate(mocker):
    mock_supabase(mocker, count_data=[], return_data=[{"id": "new-job", "status": "pending"}])
    service = AsyncJobService()

    job, is_new = await service.ensure_single_job(JobType.ANALYSIS, "user-1", {"a": 1})

    assert job == {"id": "new-job", "status": "pending"}
    assert is_new is True


# ==========================================================
# create_job
# ==========================================================

@pytest.mark.asyncio
async def test_create_job_success(mocker):
    mock_supabase(mocker, return_data=[{"id": "job-1", "status": "pending"}])
    service = AsyncJobService()

    job = await service.create_job(JobType.ANALYSIS, "user-1", {"a": 1})

    assert job == {"id": "job-1", "status": "pending"}


@pytest.mark.asyncio
async def test_create_job_raises_when_no_data_returned(mocker):
    mock_supabase(mocker, return_data=None)
    service = AsyncJobService()

    with pytest.raises(Exception, match="Failed to create job"):
        await service.create_job(JobType.ANALYSIS, "user-1", {"a": 1})


# ==========================================================
# get_job
# ==========================================================

@pytest.mark.asyncio
async def test_get_job_found(mocker):
    mock_supabase(mocker, return_data=[{"id": "job-1", "status": "completed"}])
    service = AsyncJobService()

    job = await service.get_job("job-1")

    assert job == {"id": "job-1", "status": "completed"}


@pytest.mark.asyncio
async def test_get_job_not_found(mocker):
    mock_supabase(mocker, return_data=[])
    service = AsyncJobService()

    job = await service.get_job("missing-job")

    assert job is None


# ==========================================================
# get_user_jobs
# ==========================================================

@pytest.mark.asyncio
async def test_get_user_jobs_returns_list(mocker):
    mock_supabase(mocker, return_data=[{"id": "job-1"}, {"id": "job-2"}])
    service = AsyncJobService()

    jobs = await service.get_user_jobs("user-1")

    assert jobs == [{"id": "job-1"}, {"id": "job-2"}]


@pytest.mark.asyncio
async def test_get_user_jobs_empty_when_no_data(mocker):
    mock_supabase(mocker, return_data=None)
    service = AsyncJobService()

    jobs = await service.get_user_jobs("user-1")

    assert jobs == []


# ==========================================================
# update_job_status / mark_processing / mark_completed / mark_failed
# ==========================================================

@pytest.mark.asyncio
async def test_update_job_status_with_result_only(mocker):
    mock_client = mock_supabase(mocker, return_data=None)
    service = AsyncJobService()

    await service.update_job_status("job-1", JobStatus.COMPLETED, result={"score": 90})

    update_call_args = mock_client.table.return_value.update.call_args[0][0]
    assert update_call_args["status"] == "completed"
    assert update_call_args["result"] == {"score": 90}
    assert "error_message" not in update_call_args


@pytest.mark.asyncio
async def test_update_job_status_with_error_message_only(mocker):
    """Covers the error_message branch, which nothing previously exercised."""
    mock_client = mock_supabase(mocker, return_data=None)
    service = AsyncJobService()

    await service.update_job_status("job-1", JobStatus.FAILED, error_message="boom")

    update_call_args = mock_client.table.return_value.update.call_args[0][0]
    assert update_call_args["status"] == "failed"
    assert update_call_args["error_message"] == "boom"
    assert "result" not in update_call_args


@pytest.mark.asyncio
async def test_mark_processing_sets_processing_status(mocker):
    mock_client = mock_supabase(mocker, return_data=None)
    service = AsyncJobService()

    await service.mark_processing("job-1")

    update_call_args = mock_client.table.return_value.update.call_args[0][0]
    assert update_call_args["status"] == "processing"


@pytest.mark.asyncio
async def test_mark_completed_sets_completed_status_and_result(mocker):
    mock_client = mock_supabase(mocker, return_data=None)
    service = AsyncJobService()

    await service.mark_completed("job-1", {"score": 90})

    update_call_args = mock_client.table.return_value.update.call_args[0][0]
    assert update_call_args["status"] == "completed"
    assert update_call_args["result"] == {"score": 90}


@pytest.mark.asyncio
async def test_mark_failed_sets_failed_status_and_error(mocker):
    """Covers mark_failed's body, which nothing previously called."""
    mock_client = mock_supabase(mocker, return_data=None)
    service = AsyncJobService()

    await service.mark_failed("job-1", "something broke")

    update_call_args = mock_client.table.return_value.update.call_args[0][0]
    assert update_call_args["status"] == "failed"
    assert update_call_args["error_message"] == "something broke"


# ==========================================================
# process_analysis_job: success path and exception path
# ==========================================================

@pytest.mark.asyncio
async def test_process_analysis_job_success(mocker):
    mock_client = mock_supabase(mocker, return_data=None)
    mocker.patch(
        "services.analysis_service.run_analysis",
        return_value={"score": 90},
    )
    service = AsyncJobService()

    await service.process_analysis_job("job-1", {"user_id": "user-1"})

    statuses = [
        call.args[0]["status"]
        for call in mock_client.table.return_value.update.call_args_list
    ]
    assert statuses == ["processing", "completed"]


@pytest.mark.asyncio
async def test_process_analysis_job_exception_is_caught_and_marks_failed(mocker):
    """Covers the except block -- previously untested. If run_analysis
    blows up, the job must be marked failed, not left hanging, and the
    exception must NOT propagate out of process_analysis_job."""
    mock_client = mock_supabase(mocker, return_data=None)
    mocker.patch(
        "services.analysis_service.run_analysis",
        side_effect=Exception("analysis blew up"),
    )
    service = AsyncJobService()

    # must not raise
    await service.process_analysis_job("job-1", {"user_id": "user-1"})

    statuses = [
        call.args[0]["status"]
        for call in mock_client.table.return_value.update.call_args_list
    ]
    assert statuses == ["processing", "failed"]

    failed_call_args = mock_client.table.return_value.update.call_args_list[-1].args[0]
    assert failed_call_args["error_message"] == "analysis blew up"


# ==========================================================
# module-level wrapper functions
# ==========================================================

@pytest.mark.asyncio
async def test_create_analysis_job_wrapper_delegates_correctly(mocker):
    mock_create = mocker.patch.object(
        async_job_service, "create_job", new=AsyncMock(return_value={"id": "job-1"})
    )

    result = await create_analysis_job("user-1")

    assert result == {"id": "job-1"}
    mock_create.assert_awaited_once_with(
        job_type=JobType.ANALYSIS,
        user_id="user-1",
        payload={"user_id": "user-1"},
    )


@pytest.mark.asyncio
async def test_create_analysis_job_idempotent_wrapper_delegates_correctly(mocker):
    mock_ensure = mocker.patch.object(
        async_job_service, "ensure_single_job",
        new=AsyncMock(return_value=({"id": "job-1"}, True))
    )

    job, is_new = await create_analysis_job_idempotent("user-1", duplicate_window_seconds=60)

    assert job == {"id": "job-1"}
    assert is_new is True
    mock_ensure.assert_awaited_once_with(
        job_type=JobType.ANALYSIS,
        user_id="user-1",
        payload={"user_id": "user-1"},
        duplicate_window_seconds=60,
    )


@pytest.mark.asyncio
async def test_get_job_status_wrapper_delegates_correctly(mocker):
    mock_get = mocker.patch.object(
        async_job_service, "get_job", new=AsyncMock(return_value={"id": "job-1"})
    )

    result = await get_job_status("job-1")

    assert result == {"id": "job-1"}
    mock_get.assert_awaited_once_with("job-1")


@pytest.mark.asyncio
async def test_get_user_job_history_wrapper_delegates_correctly(mocker):
    mock_get_jobs = mocker.patch.object(
        async_job_service, "get_user_jobs", new=AsyncMock(return_value=[{"id": "job-1"}])
    )

    result = await get_user_job_history("user-1", limit=5)

    assert result == [{"id": "job-1"}]
    mock_get_jobs.assert_awaited_once_with("user-1", 5)