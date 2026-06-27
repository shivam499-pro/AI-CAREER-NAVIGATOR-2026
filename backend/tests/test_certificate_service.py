"""
tests/test_certificate_service.py
Tests for CertificateService
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from services.certificate_service import CertificateService, CertificateResult
from core.gemini_transport import AsyncGeminiTransport, RateLimitError


FAKE_AI_RESPONSE = json.dumps({
    "course_name": "Machine Learning Specialization",
    "provider": "Coursera",
    "score": "95%",
    "completion_date": "March 2024",
    "duration": "3 months",
    "skills_unlocked": ["Python", "TensorFlow", "Neural Networks"],
    "certificate_weight": 7,
    "credibility": "high",
    "summary": "Proves strong ML fundamentals."
})


@pytest.fixture
def mock_transport():
    transport = AsyncMock(spec=AsyncGeminiTransport)
    transport.generate = AsyncMock(return_value=FAKE_AI_RESPONSE)
    transport.generate_multimodal = AsyncMock(return_value=FAKE_AI_RESPONSE)
    return transport


@pytest.fixture
def service(mock_transport):
    return CertificateService(transport=mock_transport)


# ── analyze() — image ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_jpeg_calls_multimodal(service, mock_transport):
    """JPEG certificate uses generate_multimodal."""
    result = await service.analyze(
        file_content=b"fake image bytes",
        filename="cert.jpg",
        mime_type="image/jpeg"
    )
    assert result.success is True
    assert result.data["course_name"] == "Machine Learning Specialization"
    assert result.data["provider"] == "Coursera"
    mock_transport.generate_multimodal.assert_called_once()
    mock_transport.generate.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_png_calls_multimodal(service, mock_transport):
    """PNG certificate uses generate_multimodal."""
    result = await service.analyze(
        file_content=b"fake png bytes",
        filename="cert.png",
        mime_type="image/png"
    )
    assert result.success is True
    mock_transport.generate_multimodal.assert_called_once()


# ── analyze() — text PDF ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_text_pdf_uses_text_path(service, mock_transport):
    """Text PDF extracts text and uses generate() not multimodal."""
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Python Machine Learning Certificate Coursera"

    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
    mock_doc.__enter__ = MagicMock(return_value=mock_doc)
    mock_doc.__exit__ = MagicMock(return_value=False)

    with patch("fitz.open", return_value=mock_doc):
        result = await service.analyze(
            file_content=b"fake pdf bytes",
            filename="cert.pdf",
            mime_type="application/pdf"
        )

    assert result.success is True
    mock_transport.generate.assert_called_once()
    mock_transport.generate_multimodal.assert_not_called()


# ── analyze() — fallback paths ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_returns_fallback_on_rate_limit(service, mock_transport):
    """Rate limit error returns fallback, not an exception."""
    mock_transport.generate_multimodal.side_effect = RateLimitError("429")

    result = await service.analyze(
        file_content=b"fake image",
        filename="cert.jpg",
        mime_type="image/jpeg"
    )

    assert result.success is True
    assert result.data["provider"] == "Unknown"
    assert result.data["certificate_weight"] == 5
    assert result.data["document_type"] == "certificate"


@pytest.mark.asyncio
async def test_analyze_returns_fallback_on_json_error(service, mock_transport):
    """Malformed JSON response returns fallback."""
    mock_transport.generate_multimodal.return_value = "not valid json {{{"

    result = await service.analyze(
        file_content=b"fake image",
        filename="my_cert.png",
        mime_type="image/png"
    )

    assert result.success is True
    assert result.data["document_type"] == "certificate"


@pytest.mark.asyncio
async def test_analyze_unsupported_type_returns_fallback(service):
    """Unsupported mime type returns fallback."""
    result = await service.analyze(
        file_content=b"fake data",
        filename="cert.gif",
        mime_type="image/gif"
    )

    assert result.success is True
    assert result.data["provider"] == "Unknown"


@pytest.mark.asyncio
async def test_analyze_fallback_cleans_filename(service, mock_transport):
    """Fallback uses cleaned filename as course_name."""
    mock_transport.generate_multimodal.side_effect = Exception("AI down")

    result = await service.analyze(
        file_content=b"bytes",
        filename="python_course_certificate.jpg",
        mime_type="image/jpeg"
    )

    assert "python course certificate" in result.data["course_name"].lower()


# ── analyze_batch() ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_batch_processes_all_files(service, mock_transport):
    """Batch analysis processes all files and returns results in order."""
    files = [
        {"content": b"img1", "filename": "cert1.jpg", "mime_type": "image/jpeg"},
        {"content": b"img2", "filename": "cert2.png", "mime_type": "image/png"},
        {"content": b"img3", "filename": "cert3.jpg", "mime_type": "image/jpeg"},
    ]

    results = await service.analyze_batch(files)

    assert len(results) == 3
    assert all(r.success is True for r in results)
    assert mock_transport.generate_multimodal.call_count == 3


@pytest.mark.asyncio
async def test_analyze_batch_respects_concurrency_limit(service, mock_transport):
    """Max concurrent calls are bounded by semaphore."""
    active_calls = 0
    max_active = 0

    async def counting_generate(contents):
        nonlocal active_calls, max_active
        active_calls += 1
        max_active = max(max_active, active_calls)
        import asyncio
        await asyncio.sleep(0.05)
        active_calls -= 1
        return FAKE_AI_RESPONSE

    mock_transport.generate_multimodal.side_effect = counting_generate

    files = [
        {"content": b"img", "filename": f"cert{i}.jpg", "mime_type": "image/jpeg"}
        for i in range(6)
    ]

    await service.analyze_batch(files, max_concurrent=2)

    assert max_active <= 2


# ── aggregate_skills() ────────────────────────────────────────────────────────

def test_aggregate_skills_deduplicates(service):
    """Skills are deduplicated case-insensitively."""
    results = [
        CertificateResult("a.jpg", True, {"skills_unlocked": ["Python", "TensorFlow"]}),
        CertificateResult("b.jpg", True, {"skills_unlocked": ["python", "AWS"]}),
        CertificateResult("c.jpg", True, {"skills_unlocked": ["AWS", "Docker"]}),
    ]

    skills = service.aggregate_skills(results)

    assert len(skills) == 4  # Python, TensorFlow, AWS, Docker
    lower = [s.lower() for s in skills]
    assert "python" in lower
    assert "tensorflow" in lower
    assert "aws" in lower
    assert "docker" in lower


def test_aggregate_skills_skips_failed_results(service):
    """Failed results are excluded from skills aggregation."""
    results = [
        CertificateResult("a.jpg", True,  {"skills_unlocked": ["Python"]}),
        CertificateResult("b.jpg", False, {"skills_unlocked": ["TensorFlow"]}),
    ]

    skills = service.aggregate_skills(results)

    assert "Python" in skills
    assert "TensorFlow" not in skills


def test_aggregate_skills_empty_results(service):
    """Empty results returns empty list."""
    assert service.aggregate_skills([]) == []


# ── CertificateResult helpers ─────────────────────────────────────────────────

def test_result_to_response_success():
    """Success result produces correct response shape."""
    result = CertificateResult(
        filename="cert.jpg",
        success=True,
        data={"course_name": "ML Course", "provider": "Coursera"}
    )
    resp = result.to_response()
    assert resp["success"] is True
    assert resp["filename"] == "cert.jpg"
    assert "extracted" in resp


def test_result_to_response_failure():
    """Failure result produces correct response shape."""
    result = CertificateResult(
        filename="bad.jpg",
        success=False,
        error="File too large"
    )
    resp = result.to_response()
    assert resp["success"] is False
    assert resp["error"] == "File too large"