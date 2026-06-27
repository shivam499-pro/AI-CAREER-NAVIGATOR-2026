"""
core/gemini_transport.py
Fix: genai.AsyncClient does not exist in google-genai 1.x.

Correct 1.x API:
  client = genai.Client(api_key=...)
  await client.aio.models.generate_content(...)
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Union

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised on 429 / RESOURCE_EXHAUSTED. Not retried."""


@dataclass
class RateLimitClassifier:
    keywords: list[str] = field(default_factory=lambda: [
        "429", "rate limit", "resource_exhausted",
        "quota exceeded", "too many requests",
    ])
    def matches(self, error: Exception) -> bool:
        return any(kw in str(error).lower() for kw in self.keywords)


@dataclass
class RetriableErrorClassifier:
    keywords: list[str] = field(default_factory=lambda: [
        "500", "502", "503", "504",
        "timeout", "timed out", "connection", "network",
    ])
    def matches(self, error: Exception) -> bool:
        return any(kw in str(error).lower() for kw in self.keywords)


@dataclass
class RetryPolicy:
    max_retries: int  = 2
    base_delay: float = 1.0

    def delay_for(self, attempt: int) -> float:
        return self.base_delay * (2 ** attempt)

    @property
    def total_attempts(self) -> int:
        return self.max_retries + 1


ContentItem = Union[dict[str, Any], genai_types.Part]


class AsyncGeminiTransport:
    """
    Async wrapper around google-genai SDK (1.x).
    Uses genai.Client with .aio namespace for async calls.
    DIP: inject client in production, mock in tests.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(
        self,
        *,
        client: genai.Client,
        model: str = DEFAULT_MODEL,
        retry_policy: RetryPolicy = None,
        rate_limit_classifier: RateLimitClassifier = None,
        retriable_classifier: RetriableErrorClassifier = None,
    ) -> None:
        self._client         = client
        self._model          = model
        self._retry          = retry_policy or RetryPolicy()
        self._rate_limit_cls = rate_limit_classifier or RateLimitClassifier()
        self._retriable_cls  = retriable_classifier or RetriableErrorClassifier()

    @classmethod
    def create(cls, model: str = DEFAULT_MODEL, retry_policy: RetryPolicy = None) -> "AsyncGeminiTransport":
        """Production factory. Reads GEMINI_API_KEY from environment."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from environment.")
        # FIX: genai.Client (not genai.AsyncClient — does not exist in 1.x)
        client = genai.Client(api_key=api_key)
        return cls(client=client, model=model, retry_policy=retry_policy)

    async def generate(self, prompt: str) -> str:
        """Send a text-only prompt and return response text."""
        return await self._call_with_retry([{"text": prompt}])

    async def generate_multimodal(self, contents: list[ContentItem]) -> str:
        """Send a multimodal request (text + image/PDF bytes)."""
        return await self._call_with_retry(contents)

    async def _call_with_retry(self, contents: list[ContentItem]) -> str:
        last_exception: Exception | None = None

        for attempt in range(self._retry.total_attempts):
            try:
                # FIX: .aio.models is the async namespace in google-genai 1.x
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,
                )
                return response.text

            except Exception as exc:
                last_exception = exc

                if self._rate_limit_cls.matches(exc):
                    logger.warning("[GeminiTransport] Rate limit attempt %d/%d: %s",
                                   attempt + 1, self._retry.total_attempts, exc)
                    raise RateLimitError(
                        "Gemini API rate limit exceeded. Please wait and try again."
                    ) from exc

                if self._retriable_cls.matches(exc):
                    if attempt < self._retry.max_retries:
                        delay = self._retry.delay_for(attempt)
                        logger.warning("[GeminiTransport] Retriable error attempt %d/%d, "
                                       "retrying in %.1fs: %s",
                                       attempt + 1, self._retry.total_attempts, delay, exc)
                        await asyncio.sleep(delay)
                        continue

                logger.error("[GeminiTransport] Non-retriable error attempt %d/%d: %s",
                             attempt + 1, self._retry.total_attempts, exc)
                raise

        raise last_exception  # type: ignore[misc]