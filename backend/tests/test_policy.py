"""
Tests for the LLM response policy checker.

Covers:
  1. Valid response passes all checks
  2. Invalid schema → validation error
  3. Unknown evidence IDs → citation error
  4. Prohibited content → content error
  5. Irreversible action keyword → warning
  6. PII / secret detection → error
"""

from __future__ import annotations

from app.services.policy_checker import (
    LLMResponse,
    PROHIBITED_PATTERNS,
    validate_llm_response,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

VALID_EVENT_IDS = {"evt_001", "evt_002", "evt_003"}


def _make_valid_response(**overrides) -> dict:
    """Return a baseline valid LLM response dict, with optional overrides."""
    base = {
        "summary": "The account shows a pattern of rapid refunds across multiple orders.",
        "evidence_ids": ["evt_001", "evt_002"],
        "risk_factors": ["High refund velocity", "Shared payment token"],
        "recommended_next_step": "Review the linked accounts and verify shipping addresses.",
        "uncertainties": ["Could not confirm device ownership."],
        "refusal_reason": None,
    }
    base.update(overrides)
    return base


# ── Tests ────────────────────────────────────────────────────────────────────


class TestPolicyChecker:
    """validate_llm_response test suite."""

    def test_valid_response_passes(self):
        """A well-formed response with valid citations should pass."""
        result = validate_llm_response(
            _make_valid_response(),
            valid_event_ids=VALID_EVENT_IDS,
        )
        assert result.valid is True
        assert result.errors == []

    def test_invalid_schema_returns_error(self):
        """Missing required fields should fail schema validation."""
        bad_response = {"summary": "Only summary, missing recommended_next_step."}
        result = validate_llm_response(bad_response, valid_event_ids=VALID_EVENT_IDS)
        assert result.valid is False
        assert any("Schema validation failed" in e for e in result.errors)
        assert result.needs_human_review is True

    def test_unknown_evidence_ids(self):
        """Citing non-existent event IDs should produce a citation error."""
        response = _make_valid_response(evidence_ids=["evt_001", "evt_FAKE_999"])
        result = validate_llm_response(response, valid_event_ids=VALID_EVENT_IDS)
        assert result.valid is False
        assert any("Citation validation failed" in e for e in result.errors)

    def test_prohibited_content_detected(self):
        """Mentioning attack techniques should trigger a prohibited-content error."""
        response = _make_valid_response(
            summary="The attacker used SQL injection to exploit the payment gateway."
        )
        result = validate_llm_response(response, valid_event_ids=VALID_EVENT_IDS)
        assert result.valid is False
        assert any("Prohibited content detected" in e for e in result.errors)

    def test_irreversible_action_warning(self):
        """Recommending 'ban' or 'suspend' should produce a warning (not an error)."""
        response = _make_valid_response(
            recommended_next_step="Immediately ban the account and suspend all pending orders."
        )
        result = validate_llm_response(response, valid_event_ids=VALID_EVENT_IDS)
        # Warnings are raised but the response is still "valid" (no hard errors)
        assert len(result.warnings) > 0
        assert any("Irreversible action" in w for w in result.warnings)

    def test_pii_detection(self):
        """Including an email address (PII) should trigger an error."""
        response = _make_valid_response(
            summary="Contact the user at fraudster@example.com for verification."
        )
        result = validate_llm_response(response, valid_event_ids=VALID_EVENT_IDS)
        assert result.valid is False
        assert any("secret/PII" in e.lower() or "PII" in e for e in result.errors)
