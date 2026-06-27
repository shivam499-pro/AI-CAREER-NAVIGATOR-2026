"""
tests/test_gemini_transport.py
Updated mocks: client.aio.models.generate_content (was client.models)
"""

from __future__ import annotations

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.gemini_transport import (
    AsyncGeminiTransport,
    RateLimitError,
    RateLimitClassifier,
    RetriableErrorClassifier,
    RetryPolicy,
)


def _make_response(text: str) -> MagicMock:
    r = MagicMock()
    r.text = text
    return r


def _make_transport(
    *,
    responses=None,
    side_effects=None,
    max_retries: int = 2,
    base_delay: float = 0.0,
) -> tuple[AsyncGeminiTransport, AsyncMock]:
    mock_client = MagicMock()
    # FIX: mock .aio.models.generate_content (not .models.generate_content)
    mock_aio_models = AsyncMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models = mock_aio_models

    if side_effects is not None:
        mock_aio_models.generate_content.side_effect = side_effects
    elif responses is not None:
        mock_aio_models.generate_content.side_effect = [
            _make_response(r) if isinstance(r, str) else r
            for r in responses
        ]

    transport = AsyncGeminiTransport(
        client=mock_client,
        retry_policy=RetryPolicy(max_retries=max_retries, base_delay=base_delay),
    )
    return transport, mock_aio_models


@pytest.mark.asyncio
async def test_generate_returns_response_text():
    transport, mock_models = _make_transport(responses=["Hello from Gemini"])
    result = await transport.generate("Tell me about Python")
    assert result == "Hello from Gemini"
    mock_models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_generate_multimodal_returns_response_text():
    transport, mock_models = _make_transport(responses=["Certificate analysis result"])
    contents = [
        {"inline_data": {"mime_type": "image/png", "data": b"fakebytes"}},
        {"text": "Analyze this certificate"},
    ]
    result = await transport.generate_multimodal(contents)
    assert result == "Certificate analysis result"
    mock_models.generate_content.assert_called_once()
    call_args = mock_models.generate_content.call_args
    assert call_args.kwargs["contents"] == contents


@pytest.mark.asyncio
async def test_rate_limit_raises_immediately_no_retry():
    rate_limit_exc = Exception("429 RESOURCE_EXHAUSTED quota exceeded")
    transport, mock_models = _make_transport(side_effects=[rate_limit_exc])
    with pytest.raises(RateLimitError):
        await transport.generate("any prompt")
    assert mock_models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_rate_limit_message_is_user_friendly():
    transport, _ = _make_transport(side_effects=[Exception("429 too many requests")])
    with pytest.raises(RateLimitError) as exc_info:
        await transport.generate("prompt")
    assert "rate limit" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_retriable_error_retries_up_to_max():
    retriable_exc = Exception("503 Service Unavailable")
    transport, mock_models = _make_transport(
        side_effects=[retriable_exc, retriable_exc, retriable_exc],
        max_retries=2, base_delay=0.0,
    )
    with pytest.raises(Exception, match="503"):
        await transport.generate("prompt")
    assert mock_models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_retriable_error_awaits_asyncio_sleep_not_time_sleep():
    retriable_exc = Exception("timeout")
    transport, _ = _make_transport(
        side_effects=[retriable_exc, _make_response("ok")],
        max_retries=2, base_delay=1.0,
    )
    with patch("core.gemini_transport.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await transport.generate("prompt")
    assert result == "ok"
    mock_sleep.assert_awaited_once()
    mock_sleep.assert_awaited_with(1.0)


@pytest.mark.asyncio
async def test_retriable_exhausted_raises_original_exception():
    retriable_exc = Exception("connection reset")
    transport, mock_models = _make_transport(
        side_effects=[retriable_exc] * 3, max_retries=2, base_delay=0.0,
    )
    with pytest.raises(Exception, match="connection reset"):
        await transport.generate("prompt")
    assert mock_models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_non_retriable_error_raises_immediately():
    non_retriable = ValueError("Invalid model parameter")
    transport, mock_models = _make_transport(side_effects=[non_retriable], max_retries=2)
    with pytest.raises(ValueError, match="Invalid model parameter"):
        await transport.generate("prompt")
    assert mock_models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_success_after_one_retriable_failure():
    retriable_exc = Exception("502 Bad Gateway")
    transport, mock_models = _make_transport(
        side_effects=[retriable_exc, _make_response("recovered")],
        max_retries=2, base_delay=0.0,
    )
    result = await transport.generate("prompt")
    assert result == "recovered"
    assert mock_models.generate_content.call_count == 2


def test_retry_policy_delay_values():
    policy = RetryPolicy(max_retries=2, base_delay=1.0)
    assert policy.delay_for(0) == 1.0
    assert policy.delay_for(1) == 2.0
    assert policy.delay_for(2) == 4.0


def test_retry_policy_total_attempts():
    assert RetryPolicy(max_retries=2).total_attempts == 3


@pytest.mark.parametrize("error_msg", [
    "429 error", "rate limit exceeded", "RESOURCE_EXHAUSTED",
    "quota exceeded", "too many requests",
])
def test_rate_limit_classifier_matches_all_production_keywords(error_msg):
    assert RateLimitClassifier().matches(Exception(error_msg)) is True


def test_rate_limit_classifier_does_not_match_retriable():
    assert RateLimitClassifier().matches(Exception("503 Service Unavailable")) is False


@pytest.mark.parametrize("error_msg", [
    "500 Internal Server Error", "502 Bad Gateway", "503 Service Unavailable",
    "504 Gateway Timeout", "timeout waiting for response", "request timed out",
    "connection refused", "network unreachable",
])
def test_retriable_classifier_matches_all_production_keywords(error_msg):
    assert RetriableErrorClassifier().matches(Exception(error_msg)) is True


def test_retriable_classifier_does_not_match_rate_limit():
    assert RetriableErrorClassifier().matches(Exception("429 too many requests")) is False


def test_create_raises_without_api_key():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("GEMINI_API_KEY", None)
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            AsyncGeminiTransport.create()


@pytest.mark.asyncio
async def test_injected_client_is_used_not_real_api():
    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=_make_response("mocked response")
    )
    transport = AsyncGeminiTransport(
        client=mock_client,
        retry_policy=RetryPolicy(max_retries=0, base_delay=0.0),
    )
    result = await transport.generate("test prompt")
    assert result == "mocked response"
    mock_client.aio.models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_generate_passes_correct_model_and_contents():
    transport, mock_models = _make_transport(responses=["ok"])
    await transport.generate("my prompt")
    call_kwargs = mock_models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == AsyncGeminiTransport.DEFAULT_MODEL
    assert call_kwargs["contents"] == [{"text": "my prompt"}]


@pytest.mark.asyncio
async def test_custom_model_is_used():
    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=_make_response("ok"))
    transport = AsyncGeminiTransport(
        client=mock_client, model="gemini-1.5-pro",
        retry_policy=RetryPolicy(max_retries=0),
    )
    await transport.generate("prompt")
    call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-1.5-pro"


@pytest.mark.asyncio
async def test_concurrent_requests_do_not_share_state():
    call_count = 0

    async def fake_generate_content(*, model, contents):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0)
        return _make_response(f"response_{call_count}")

    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models.generate_content.side_effect = fake_generate_content

    transport = AsyncGeminiTransport(
        client=mock_client, retry_policy=RetryPolicy(max_retries=0),
    )
    results = await asyncio.gather(
        transport.generate("prompt A"),
        transport.generate("prompt B"),
    )
    assert len(results) == 2
    assert call_count == 2