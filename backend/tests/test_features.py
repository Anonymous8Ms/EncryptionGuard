"""
Tests for the shared feature library (FeatureVector).

Covers:
- Default field values
- Serialization round-trip (dict → FeatureVector → dict)
- Field types (int, float, Optional)
"""

import pytest
from datetime import datetime, timezone

from backend.features.schema import FeatureVector


class TestFeatureVectorDefaults:
    """FeatureVector should have sensible defaults for all fields."""

    def test_minimal_construction(self):
        """Creating a FeatureVector with only required fields should succeed."""
        fv = FeatureVector(
            account_id="acct_001",
            merchant_id="mrc_001",
            reference_timestamp=datetime.now(timezone.utc),
        )
        assert fv.account_id == "acct_001"
        assert fv.merchant_id == "mrc_001"

    def test_velocity_defaults_are_zero(self):
        """All velocity features should default to 0."""
        fv = FeatureVector(
            account_id="acct_001",
            merchant_id="mrc_001",
            reference_timestamp=datetime.now(timezone.utc),
        )
        assert fv.refund_count_24h == 0
        assert fv.refund_count_7d == 0
        assert fv.refund_count_30d == 0
        assert fv.refund_amount_24h == 0.0
        assert fv.refund_amount_7d == 0.0
        assert fv.refund_amount_30d == 0.0
        assert fv.order_count_24h == 0
        assert fv.order_count_7d == 0
        assert fv.order_count_30d == 0
        assert fv.unique_device_count == 0
        assert fv.unique_ip_count == 0
        assert fv.unique_token_count == 0

    def test_graph_defaults_are_zero_or_none(self):
        """Graph features should default to 0 or None."""
        fv = FeatureVector(
            account_id="acct_001",
            merchant_id="mrc_001",
            reference_timestamp=datetime.now(timezone.utc),
        )
        assert fv.connected_component_size == 0
        assert fv.weighted_degree == 0.0
        assert fv.pagerank_score is None
        assert fv.community_id is None
        assert fv.shared_device_count == 0
        assert fv.shared_ip_count == 0
        assert fv.shared_token_count == 0

    def test_label_defaults_are_none(self):
        """Training labels should default to None."""
        fv = FeatureVector(
            account_id="acct_001",
            merchant_id="mrc_001",
            reference_timestamp=datetime.now(timezone.utc),
        )
        assert fv.event_label is None
        assert fv.ring_id is None
        assert fv.scenario_id is None


class TestFeatureVectorSerialization:
    """FeatureVector should round-trip through dict/JSON."""

    def test_dict_round_trip(self):
        """dict() → FeatureVector(**d) should preserve all values."""
        now = datetime.now(timezone.utc)
        original = FeatureVector(
            account_id="acct_002",
            merchant_id="mrc_002",
            reference_timestamp=now,
            refund_count_24h=3,
            refund_amount_24h=450.0,
            connected_component_size=5,
            pagerank_score=0.042,
            event_label="fraud",
            ring_id="ring_abc",
        )
        d = original.model_dump()
        restored = FeatureVector(**d)

        assert restored.account_id == original.account_id
        assert restored.refund_count_24h == original.refund_count_24h
        assert restored.refund_amount_24h == original.refund_amount_24h
        assert restored.connected_component_size == original.connected_component_size
        assert restored.pagerank_score == original.pagerank_score
        assert restored.event_label == original.event_label
        assert restored.ring_id == original.ring_id

    def test_json_round_trip(self):
        """model_dump_json() → model_validate_json() should preserve values."""
        now = datetime.now(timezone.utc)
        original = FeatureVector(
            account_id="acct_003",
            merchant_id="mrc_003",
            reference_timestamp=now,
            refund_count_7d=10,
            weighted_degree=3.5,
            community_id=7,
        )
        json_str = original.model_dump_json()
        restored = FeatureVector.model_validate_json(json_str)

        assert restored.account_id == original.account_id
        assert restored.refund_count_7d == original.refund_count_7d
        assert restored.weighted_degree == original.weighted_degree
        assert restored.community_id == original.community_id


class TestFeatureVectorTypes:
    """Field types should be enforced by Pydantic."""

    def test_integer_fields_reject_strings(self):
        """Integer fields should reject non-numeric values."""
        with pytest.raises(Exception):  # ValidationError
            FeatureVector(
                account_id="acct_004",
                merchant_id="mrc_004",
                reference_timestamp=datetime.now(timezone.utc),
                refund_count_24h="not_a_number",
            )

    def test_float_fields_accept_ints(self):
        """Float fields should accept integer values (coerced to float)."""
        fv = FeatureVector(
            account_id="acct_005",
            merchant_id="mrc_005",
            reference_timestamp=datetime.now(timezone.utc),
            refund_amount_24h=100,  # int → float
        )
        assert isinstance(fv.refund_amount_24h, float)
        assert fv.refund_amount_24h == 100.0

    def test_optional_fields_accept_none(self):
        """Optional fields should accept None explicitly."""
        fv = FeatureVector(
            account_id="acct_006",
            merchant_id="mrc_006",
            reference_timestamp=datetime.now(timezone.utc),
            pagerank_score=None,
            community_id=None,
            event_label=None,
            ring_id=None,
            scenario_id=None,
        )
        assert fv.pagerank_score is None
        assert fv.community_id is None
        assert fv.event_label is None
