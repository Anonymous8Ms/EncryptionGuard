"""
EncryptionGuard v5 — LLM service (Xiaomi MiMo API).

Calls the MiMo v2.5-pro model to summarise evidence bundles and answer
analyst questions.  The LLM is NOT the fraud detector — it only produces
structured summaries that a human analyst reviews.

Key design points:
  - Strict JSON-only system prompt with schema requirements.
  - 3 retries with exponential backoff on transient failures.
  - Deterministic fallback on total failure (never blocks the pipeline).
  - All output is validated by policy_checker before reaching the analyst.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

MODEL = "mimo-v2.5-pro"
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0  # doubles each retry: 1s, 2s, 4s
REQUEST_TIMEOUT_SECONDS = 60.0

SYSTEM_PROMPT = """\
You are an evidence-analysis assistant for a fraud-investigation platform.

RULES — you MUST follow every one:
1. Return ONLY valid JSON matching the schema below.  No markdown, no prose
   outside the JSON object.
2. NEVER recommend irreversible actions (ban, block, suspend, delete, etc.).
   Only suggest what the analyst should review next.
3. NEVER discuss attack techniques, exploitation methods, or how to commit fraud.
4. NEVER include raw secrets, passwords, API keys, credit-card numbers, or PII.
5. Every evidence_ids entry MUST be an event ID from the provided bundle.
   Do NOT invent or hallucinate IDs.
6. If you cannot determine something, list it in "uncertainties" — do NOT guess.
7. If the evidence is insufficient to form a conclusion, set refusal_reason
   and leave other fields empty/neutral.

JSON SCHEMA (you MUST return exactly these keys):
{
  "summary": "<string — concise summary of the evidence bundle>",
  "evidence_ids": ["<event_id_1>", "<event_id_2>"],
  "risk_factors": ["<risk factor 1>", "<risk factor 2>"],
  "recommended_next_step": "<string — what the analyst should do next>",
  "uncertainties": ["<gap or unknown 1>"],
  "refusal_reason": null
}

If you refuse to answer, set refusal_reason to a string explaining why and
set summary to "Refused", evidence_ids to [], risk_factors to [],
recommended_next_step to "Manual review required", and uncertainties to [].
"""


# ── Public API ───────────────────────────────────────────────────────────────

async def analyze_case(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    """Send an evidence bundle to MiMo and return a structured analysis.

    Args:
        evidence_bundle: Dict containing case_id, events, metadata, etc.

    Returns:
        Parsed JSON dict matching the schema in SYSTEM_PROMPT.
        On total failure, returns a safe fallback response.
    """
    user_message = json.dumps(evidence_bundle, default=str, ensure_ascii=False)

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await _call_mimo(user_message)
            parsed = _parse_response(response)
            logger.info(
                "LLM analysis succeeded on attempt %d for case %s",
                attempt,
                evidence_bundle.get("case_id", "unknown"),
            )
            return parsed
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            wait = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "LLM attempt %d/%d failed: %s — retrying in %.1fs",
                attempt,
                MAX_RETRIES,
                exc,
                wait,
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(wait)

    # All retries exhausted — fall back
    logger.error(
        "All %d LLM attempts failed for case %s. Last error: %s",
        MAX_RETRIES,
        evidence_bundle.get("case_id", "unknown"),
        last_error,
    )
    return _fallback_response(str(last_error))


# ── Internal helpers ─────────────────────────────────────────────────────────

async def _call_mimo(user_message: str) -> httpx.Response:
    """Make a single chat-completion request to the MiMo API."""
    url = f"{settings.mimo_api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.mimo_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    """Extract and validate the JSON content from a MiMo chat response."""
    body = response.json()

    # OpenAI-compatible response structure
    choices = body.get("choices", [])
    if not choices:
        raise ValueError("No choices in LLM response")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("Empty content in LLM response")

    # Parse JSON — the system prompt demands JSON-only output
    parsed = json.loads(content)

    # Quick structural sanity check
    required_keys = {"summary", "evidence_ids", "risk_factors", "recommended_next_step"}
    missing = required_keys - set(parsed.keys())
    if missing:
        raise ValueError(f"LLM response missing required keys: {missing}")

    return parsed


def _fallback_response(reason: str) -> dict[str, Any]:
    """Return a safe default response when the LLM is unreachable.

    This ensures the pipeline never blocks — the analyst always gets
    something to review, even if it's just "manual review required".
    """
    return {
        "summary": "LLM analysis unavailable. Manual review required.",
        "evidence_ids": [],
        "risk_factors": [],
        "recommended_next_step": "Manual review required — LLM service "
        "was unable to process this case.",
        "uncertainties": [
            "LLM service failure — no automated analysis available.",
            f"Failure reason: {reason}",
        ],
        "refusal_reason": f"Service failure: {reason}",
    }
