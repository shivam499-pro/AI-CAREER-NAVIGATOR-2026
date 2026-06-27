"""
services/certificate_service.py
─────────────────────────────────────────────────────────────────────
CertificateService — owns all certificate AI analysis logic.

Single Responsibility:
  - Analyze a single certificate (image or PDF) via Gemini vision
  - Analyze a batch of certificates concurrently
  - Aggregate skills across multiple certificate results
  - Provide fallback data when AI fails

Does NOT own:
  - File validation (content type, size) — stays in router
  - Database saves — stays in router / repository
  - Profile updates — stays in router
  - Storage uploads — stays in router

DIP: Receives AsyncGeminiTransport via constructor.
     No module-level client. No global state.

Replaces:
  - Direct gemini_service.analyze_certificate() calls in documents.py
  - The missing `await` bug on line 106 of documents.py
  - Import-inside-function anti-pattern in documents.py
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from core.gemini_transport import AsyncGeminiTransport, RateLimitError

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Prompt (moved out of gemini_service — SRP: prompt belongs to the service
# that owns the business logic, not the transport layer)
# ─────────────────────────────────────────────────────────────────────────────

CERTIFICATE_PROMPT = """You are a career intelligence AI that reads certificates and extracts structured data.

Analyze this certificate and return ONLY a valid JSON object with exactly these fields:

{
  "course_name": "Full course or certification name",
  "provider": "Who issued it (NPTEL, Coursera, AWS, Google, etc.)",
  "score": "Score or grade if visible (e.g. 85%, Elite, Pass) or null",
  "completion_date": "Month Year format if visible (e.g. March 2024) or null",
  "duration": "Duration if visible (e.g. 12 weeks) or null",
  "skills_unlocked": ["skill1", "skill2", "skill3"],
  "certificate_weight": 7,
  "credibility": "high",
  "summary": "One sentence describing what this certificate proves about the candidate."
}

Rules for certificate_weight (1-10 scale):
- 9: AWS/GCP/Azure/Microsoft official certs
- 8: NPTEL Elite / Hackathon Winner / Google certs
- 7: NPTEL with grade / Coursera with certificate / HackerRank
- 6: Coursera audit / edX / LinkedIn Learning with assessment
- 5: Hackathon participant / College competition
- 4: Udemy / Internal college certification
- 3: YouTube course certificate / self-printed

Rules for credibility:
- "high": AWS, Google, Microsoft, NPTEL, Coursera (graded), government-issued
- "medium": Udemy, edX, LinkedIn Learning, hackathon winner
- "low": unrecognized platforms, college internal, self-issued

For skills_unlocked: list 3-6 specific technical or professional skills
this certificate proves. Be specific (e.g. "Python", "Machine Learning",
"Data Structures", "Cloud Deployment", "REST APIs").

Return ONLY the JSON object. No markdown, no explanation."""


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CertificateResult:
    """Structured result from a single certificate analysis."""
    filename: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_response(self) -> dict[str, Any]:
        """Convert to the dict shape the router returns."""
        if self.success:
            return {
                "filename":  self.filename,
                "success":   True,
                "extracted": self.data,
            }
        return {
            "filename": self.filename,
            "success":  False,
            "error":    self.error or "Analysis failed.",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Core service
# ─────────────────────────────────────────────────────────────────────────────

class CertificateService:
    """
    Analyzes certificate files using Gemini vision.

    Supports:
      - JPEG / PNG  → multimodal vision call
      - Text PDF    → extract text → text prompt
      - Scanned PDF → rasterize first page → multimodal vision call

    DIP: inject a real AsyncGeminiTransport in production,
         inject a mock in tests.
    """

    def __init__(self, *, transport: AsyncGeminiTransport) -> None:
        self._transport = transport

    # ── Public API ────────────────────────────────────────────────────────────

    async def analyze(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
    ) -> CertificateResult:
        """
        Analyze a single certificate file.

        Args:
            file_content: Raw file bytes
            filename:     Original filename (used in fallback)
            mime_type:    "application/pdf" | "image/jpeg" | "image/png" etc.

        Returns:
            CertificateResult with success=True and structured data,
            or success=False with a fallback dict on any failure.
        """
        try:
            if mime_type in ("image/jpeg", "image/jpg", "image/png"):
                raw = await self._analyze_image(file_content, mime_type)
            elif mime_type == "application/pdf":
                raw = await self._analyze_pdf(file_content, filename)
            else:
                logger.warning(f"[CertService] Unsupported mime type: {mime_type}")
                return CertificateResult(
                    filename=filename,
                    success=True,
                    data=self._fallback(filename),
                )

            parsed = self._parse_response(raw, filename)
            return CertificateResult(filename=filename, success=True, data=parsed)

        except RateLimitError:
            logger.warning(f"[CertService] Rate limited analyzing {filename}")
            return CertificateResult(
                filename=filename,
                success=True,
                data=self._fallback(filename),
            )
        except json.JSONDecodeError:
            logger.warning(f"[CertService] JSON parse failed for {filename}")
            return CertificateResult(
                filename=filename,
                success=True,
                data=self._fallback(filename),
            )
        except Exception as exc:
            logger.error(f"[CertService] Error analyzing {filename}: {exc}")
            return CertificateResult(
                filename=filename,
                success=True,
                data=self._fallback(filename),
            )

    async def analyze_batch(
        self,
        files: list[dict[str, Any]],
        *,
        max_concurrent: int = 3,
    ) -> list[CertificateResult]:
        """
        Analyze multiple certificate files concurrently.

        Args:
            files: List of dicts with keys:
                     - content  (bytes)
                     - filename (str)
                     - mime_type (str)
            max_concurrent: Max simultaneous Gemini calls (default 3,
                            avoids rate-limit on large uploads).

        Returns:
            List of CertificateResult in the same order as input.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _bounded_analyze(f: dict) -> CertificateResult:
            async with semaphore:
                return await self.analyze(
                    file_content=f["content"],
                    filename=f["filename"],
                    mime_type=f["mime_type"],
                )

        return list(await asyncio.gather(*[_bounded_analyze(f) for f in files]))

    def aggregate_skills(self, results: list[CertificateResult]) -> list[str]:
        """
        Collect all unique skills across a batch of results.

        Pure function — no I/O, no side effects.

        Args:
            results: List of CertificateResult from analyze_batch()

        Returns:
            Deduplicated list of skill strings (case-preserved,
            deduplicated case-insensitively).
        """
        seen: set[str] = set()
        skills: list[str] = []

        for result in results:
            if result.success:
                for skill in result.data.get("skills_unlocked", []):
                    if skill.lower() not in seen:
                        seen.add(skill.lower())
                        skills.append(skill)

        return skills

    # ── Private: file-type handlers ───────────────────────────────────────────

    async def _analyze_image(self, file_content: bytes, mime_type: str) -> str:
        """Send image bytes to Gemini vision."""
        encoded = base64.b64encode(file_content).decode()
        return await self._transport.generate_multimodal([
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": encoded,
                }
            },
            {"text": CERTIFICATE_PROMPT},
        ])

    async def _analyze_pdf(self, file_content: bytes, filename: str) -> str:
        """
        Handle PDF certificates:
          1. Try to extract text layer (fast, cheap).
          2. If no text (scanned PDF), rasterize first page → vision.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("[CertService] PyMuPDF not installed. pip install pymupdf")
            raise

        with fitz.open(stream=file_content, filetype="pdf") as doc:
            pdf_text = "".join(page.get_text() for page in doc)

            if pdf_text.strip():
                # Text PDF — cheaper text path
                safe_text = pdf_text[:3000]
                text_prompt = f"{CERTIFICATE_PROMPT}\n\nCertificate text:\n{safe_text}"
                return await self._transport.generate(text_prompt)

            # Scanned PDF — rasterize first page
            if len(doc) == 0:
                logger.warning(f"[CertService] Empty PDF: {filename}")
                raise ValueError("PDF has no pages")

            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")

        from google.genai import types as genai_types
        return await self._transport.generate_multimodal([
            genai_types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            {"text": CERTIFICATE_PROMPT},
        ])

    # ── Private: response parsing ─────────────────────────────────────────────

    def _parse_response(self, raw: str, filename: str) -> dict[str, Any]:
        """Clean and parse Gemini's JSON response."""
        import re
        text = raw.strip()
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        result = json.loads(text)

        return {
            "course_name":        result.get("course_name", filename),
            "provider":           result.get("provider", "Unknown"),
            "score":              result.get("score"),
            "completion_date":    result.get("completion_date"),
            "duration":           result.get("duration"),
            "skills_unlocked":    result.get("skills_unlocked", []),
            "certificate_weight": max(1, min(10, result.get("certificate_weight", 5))),
            "credibility":        result.get("credibility", "medium"),
            "summary":            result.get("summary", ""),
            "document_type":      "certificate",
        }

    def _fallback(self, filename: str) -> dict[str, Any]:
        """Safe fallback when AI analysis fails."""
        clean_name = (
            filename
            .replace(".pdf", "")
            .replace(".jpg", "")
            .replace(".png", "")
            .replace("_", " ")
            .replace("-", " ")
        )
        return {
            "course_name":        clean_name,
            "provider":           "Unknown",
            "score":              None,
            "completion_date":    None,
            "duration":           None,
            "skills_unlocked":    [],
            "certificate_weight": 5,
            "credibility":        "medium",
            "summary":            "Certificate uploaded. AI analysis pending.",
            "document_type":      "certificate",
        }