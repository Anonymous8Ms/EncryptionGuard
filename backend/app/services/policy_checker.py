"""
EncryptionGuard v5 — Deterministic policy checker for LLM responses.

Validates every LLM output against strict rules BEFORE it reaches an analyst:
  1. Schema validation (Pydantic)
  2. Citation validation (all cited event IDs must exist in the case)
  3. Prohibited content check (regex patterns for dangerous terms)
  4. Irreversible action check (ban, block, suspend, etc.)
  5. Secret / PII redaction check

The LLM is NOT the fraud detector.  It only summarises evidence and answers
analyst questions.  This checker enforces that boundary.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── Pydantic response model ─────────────────────────────────────────────────

class LLMResponse(BaseModel):
    """Strict schema for the LLM's structured JSON output."""

    summary: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Concise summary of the evidence bundle.",
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Event / evidence IDs cited in the summary.",
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Identified risk factors (human-readable phrases).",
    )
    recommended_next_step: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="What the analyst should do next.",
    )
    uncertainties: list[str] = Field(
        default_factory=list,
        description="Gaps or unknowns the LLM could not resolve.",
    )
    refusal_reason: str | None = Field(
        default=None,
        description="If the LLM refused to answer, why.",
    )

    @field_validator("evidence_ids", mode="before")
    @classmethod
    def _coerce_evidence_ids(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return [str(x) for x in v]

    @field_validator("risk_factors", "uncertainties", mode="before")
    @classmethod
    def _coerce_str_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return [str(x) for x in v]


# ── Prohibited content patterns ─────────────────────────────────────────────

PROHIBITED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bhack(?:ing|er)?\b",
        r"\bexploit(?:ing|ation)?\b",
        r"\bbypass(?:ing)?\b",
        r"\bmalware\b",
        r"\bransomware\b",
        r"\bphish(?:ing)?\b",
        r"\bkeylog(?:ger|ging)?\b",
        r"\brootkit\b",
        r"\btrojan\b",
        r"\bbackdoor\b",
        r"\bcredential(?:s)?\s*(?:dump|stuff|theft)",
        r"\bpassword\s*(?:crack|brute|spray)",
        r"\binjection\s*(?:attack|payload)",
        r"\bSQL\s*injection",
        r"\bXSS\s*(?:attack|payload)",
        r"\bDDoS\b",
        r"\bbotnet\b",
        r"\bc2\s*(?:server|channel)",
        r"\bcommand\s*and\s*control\b",
        r"\bexfiltrat(?:e|ion|ing)\b",
        r"\blateral\s*movement\b",
        r"\bprivilege\s*escalat(?:e|ion|ing)\b",
        r"\bpersistence\s*mechanism",
    ]
]

# ── Irreversible action keywords ────────────────────────────────────────────

IRREVERSIBLE_ACTIONS: list[str] = [
    "ban",
    "block",
    "suspend",
    "terminate",
    "delete",
    "remove",
    "disable",
    "lock",
    "freeze",
    "confiscate",
    "seize",
    "permanently",
    "immediately close",
    "shut down",
]

# ── Secret / PII patterns ───────────────────────────────────────────────────

SECRET_PII_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # Credit card numbers (simplified)
        r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
        # SSN-like
        r"\b\d{3}-\d{2}-\d{4}\b",
        # API keys / tokens (common prefixes)
        r"\b(?:sk|pk|api)[_-][A-Za-z0-9]{20,}\b",
        # AWS-style keys
        r"\bAKIA[0-9A-Z]{16}\b",
        # Email addresses (PII)
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        # Phone numbers (international)
        r"\+\d{1,3}[\s-]?\d{4,14}\b",
        # Passwords in text
        r"(?i)password\s*[:=]\s*\S+",
        r"(?i)secret\s*[:=]\s*\S+",
        r"(?i)token\s*[:=]\s*\S+",
    ]
]


# ── Validation result ───────────────────────────────────────────────────────

class ValidationResult(BaseModel):
    """Output of the policy checker."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    needs_human_review: bool = False


# ── Main validation function ────────────────────────────────────────────────

def validate_llm_response(
    response: dict[str, Any],
    valid_event_ids: set[str],
    case_evidence: dict[str, Any] | None = None,
) -> ValidationResult:
    """Validate an LLM response against all policy checks.

    Args:
        response: Raw dict from the LLM (will be parsed into LLMResponse).
        valid_event_ids: Set of event IDs that actually exist in the case.
        case_evidence: Optional full evidence bundle for deeper checks.

    Returns:
        ValidationResult with valid flag, errors, warnings, and
        needs_human_review flag.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── 1. Schema validation ────────────────────────────────────────────
    try:
        parsed = LLMResponse.model_validate(response)
    except Exception as exc:
        return ValidationResult(
            valid=False,
            errors=[f"Schema validation failed: {exc}"],
            needs_human_review=True,
        )

    # ── 2. Citation validation ──────────────────────────────────────────
    if parsed.evidence_ids:
        cited = set(parsed.evidence_ids)
        missing = cited - valid_event_ids
        if missing:
            errors.append(
                f"Citation validation failed: unknown event IDs {missing}. "
                f"LLM must only cite IDs from the provided evidence bundle."
            )

    # ── 3. Prohibited content check ─────────────────────────────────────
    all_text = " ".join(
        [parsed.summary, parsed.recommended_next_step]
        + parsed.risk_factors
        + parsed.uncertainties
    )
    if parsed.refusal_reason:
        all_text += " " + parsed.refusal_reason

    for pattern in PROHIBITED_PATTERNS:
        matches = pattern.findall(all_text)
        if matches:
            errors.append(
                f"Prohibited content detected: pattern '{pattern.pattern}' "
                f"matched {len(matches)} time(s). LLM must not discuss "
                f"attack techniques or exploitation methods."
            )

    # ── 4. Irreversible action check ────────────────────────────────────
    next_step_lower = parsed.recommended_next_step.lower()
    for action in IRREVERSIBLE_ACTIONS:
        if action in next_step_lower:
            warnings.append(
                f"Irreversible action keyword '{action}' found in "
                f"recommended_next_step. The LLM must NOT recommend "
                f"irreversible actions — only suggest analyst review steps."
            )

    # ── 5. Secret / PII redaction check ─────────────────────────────────
    for pattern in SECRET_PII_PATTERNS:
        matches = pattern.findall(all_text)
        if matches:
            errors.append(
                f"Potential secret/PII detected: pattern '{pattern.pattern}' "
                f"matched {_len_matches(matches)} time(s). "
                f"LLM output must not contain raw secrets or PII."
            )

    # ── Determine final result ──────────────────────────────────────────
    needs_review = bool(errors) or any(
        kw in next_step_lower
        for kw in ["manual review", "escalate", "human", "investigate further"]
    )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        needs_human_review=needs_review,
    )


def _len_matches(matches: list[str]) -> int:
    """Safely count matches."""
    return len(matches) if isinstance(matches, list) else 1
